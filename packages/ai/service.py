import json
import os
from openai import OpenAI
from packages.mcp.registry import get_tools, call_tool, propose_action


_SYSTEM_PROMPT = """You are an AI assistant for Nova ERP, an enterprise resource planning system.
You can answer questions about ERP concepts and use the available tools to look up or modify data in the system.
When the user asks about specific records (products, orders, customers, etc.), use the appropriate tool to fetch the data.
If a tool returns data, present it clearly to the user. If you cannot fulfill a request with the available tools, explain what you can do instead.
Be concise and professional."""


def _build_openai_tools():
    tools = get_tools()
    if not tools:
        return None
    result = []
    for t in tools:
        desc = t.description
        if t.tier == "tier2":
            desc = f"[REQUIRES CONFIRMATION] {desc}"
        result.append({
            "type": "function",
            "function": {
                "name": t.name,
                "description": desc,
                "parameters": t.input_schema,
            },
        })
    return result if result else None


def _to_openai_messages(history, message):
    msgs = [{"role": "system", "content": _SYSTEM_PROMPT}]
    for h in history:
        msg = {"role": h.role, "content": h.content}
        if h.tool_calls:
            msg["tool_calls"] = h.tool_calls
        if h.tool_call_id:
            msg["tool_call_id"] = h.tool_call_id
        msgs.append(msg)
    msgs.append({"role": "user", "content": message})
    return msgs


def stream_chat(history, message, user: dict | None = None):
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        yield f"data: {json.dumps({'type': 'error', 'content': 'OpenAI API key not configured. Set OPENAI_API_KEY in your .env file.'})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        return

    client = OpenAI(api_key=api_key)
    messages = _to_openai_messages(history, message)
    openai_tools = _build_openai_tools()
    tool_tier_map = {t.name: t.tier for t in get_tools()}

    while True:
        response = client.chat.completions.create(
            model=os.getenv("OPENAI_MODEL", "gpt-4o"),
            messages=messages,
            tools=openai_tools,
            stream=True,
        )

        text_parts = []
        tool_calls = {}

        for chunk in response:
            delta = chunk.choices[0].delta if chunk.choices else None
            if not delta:
                continue
            if delta.content:
                text_parts.append(delta.content)
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    idx = tc.index
                    if idx not in tool_calls:
                        tool_calls[idx] = {"id": "", "function": {"name": "", "arguments": ""}}
                    if tc.id:
                        tool_calls[idx]["id"] = tc.id
                    if tc.function:
                        if tc.function.name:
                            tool_calls[idx]["function"]["name"] += tc.function.name
                        if tc.function.arguments:
                            tool_calls[idx]["function"]["arguments"] += tc.function.arguments

        full_text = "".join(text_parts) if text_parts else None

        if tool_calls:
            if full_text:
                yield f"data: {json.dumps({'type': 'text', 'content': full_text})}\n\n"
            assistant_msg = {"role": "assistant", "content": full_text}
            assistant_msg["tool_calls"] = [
                {"id": tc["id"], "type": "function",
                 "function": {"name": tc["function"]["name"], "arguments": tc["function"]["arguments"]}}
                for tc in tool_calls.values()
            ]
            messages.append(assistant_msg)
            yield f"data: {json.dumps({'type': 'tool_start'})}\n\n"
            for tc in tool_calls.values():
                name = tc["function"]["name"]
                try:
                    args = json.loads(tc["function"]["arguments"]) if tc["function"]["arguments"] else {}
                    tier = tool_tier_map.get(name, "tier1")
                    if tier == "tier2":
                        proposal = propose_action(name, args)
                        yield f"data: {json.dumps({'type': 'confirmation_required', 'action_id': proposal['action_id'], 'tool': name, 'preview': proposal['preview']})}\n\n"
                        result = proposal
                    else:
                        result = call_tool(name, args, user=user)
                except Exception as e:
                    result = {"error": str(e)}
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": json.dumps(result, default=str),
                })
            yield f"data: {json.dumps({'type': 'tool_end'})}\n\n"
            continue

        if full_text:
            yield f"data: {json.dumps({'type': 'text', 'content': full_text})}\n\n"
        yield f"data: {json.dumps({'type': 'done'})}\n\n"
        break
