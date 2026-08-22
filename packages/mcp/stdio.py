import os
import sys
import json
from packages.mcp.server import McpServer


def run_stdio(server: McpServer, user: dict | None = None):
    """Run MCP server in stdio mode, reading JSON-RPC from stdin and writing to stdout.

    If user is not provided, constructs user context from environment variables
    (e.g., NOVA_TENANT_ID, NOVA_USER_ID, NOVA_API_KEY).
    """
    if user is None:
        env_tenant = os.environ.get("NOVA_TENANT_ID")
        env_user_id = os.environ.get("NOVA_USER_ID")
        env_api_key = os.environ.get("NOVA_API_KEY")
        if env_tenant or env_user_id or env_api_key:
            user = {}
            if env_tenant:
                try:
                    user["business_id"] = int(env_tenant)
                except (ValueError, TypeError):
                    pass
            if env_user_id:
                try:
                    user["id"] = int(env_user_id)
                except (ValueError, TypeError):
                    pass
            if env_api_key:
                user["api_key"] = env_api_key

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        request = json.loads(line)
        response = server.handle_request(request, user=user)
        if response is not None:
            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
