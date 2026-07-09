#!/usr/bin/env python3
"""CLI launcher for any Nova ERP MCP server.

Usage:
    python scripts/run-mcp-server.py inventory
    python scripts/run-mcp-server.py sales --port 8080
    python scripts/run-mcp-server.py --list

Available servers: database, inventory, sales, purchasing, accounting,
                   admin, warehouse, hr, bi, crm, projects,
                   manufacturing, maintenance, notifications
"""

import sys
import os
import argparse

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT_DIR)

SERVERS = {
    "database": "packages.mcp.servers.database_mcp",
    "inventory": "packages.mcp.servers.inventory_mcp",
    "sales": "packages.mcp.servers.sales_mcp",
    "purchasing": "packages.mcp.servers.purchasing_mcp",
    "accounting": "packages.mcp.servers.accounting_mcp",
    "admin": "packages.mcp.servers.admin_mcp",
    "warehouse": "packages.mcp.servers.warehouse_mcp",
    "hr": "packages.mcp.servers.hr_mcp",
    "bi": "packages.mcp.servers.bi_mcp",
    "crm": "packages.mcp.servers.crm_mcp",
    "projects": "packages.mcp.servers.projects_mcp",
    "manufacturing": "packages.mcp.servers.manufacturing_mcp",
    "maintenance": "packages.mcp.servers.maintenance_mcp",
    "notifications": "packages.mcp.servers.notifications_mcp",
}


def main():
    parser = argparse.ArgumentParser(description="Launch a Nova ERP MCP server")
    parser.add_argument("server", nargs="?", help="MCP server name to launch")
    parser.add_argument("--list", action="store_true", help="List available servers")
    parser.add_argument("--port", type=int, default=None, help="HTTP port for SSE mode (stdin/stdout if omitted)")
    args = parser.parse_args()

    if args.list or not args.server:
        print("Available MCP servers:")
        for name in sorted(SERVERS):
            print(f"  {name}")
        return

    mod_path = SERVERS.get(args.server)
    if not mod_path:
        print(f"Unknown server: {args.server}", file=sys.stderr)
        print(f"Use --list to see available servers", file=sys.stderr)
        sys.exit(1)

    import importlib
    mod = importlib.import_module(mod_path)

    if args.port:
        from packages.mcp.server import McpServer
        from packages.mcp.sse import run_sse_server
        mod.register_tools()
        server = McpServer(name=f"{args.server}-mcp", version="1.0")
        print(f"Starting {args.server}-mcp on port {args.port}", file=sys.stderr)
        run_sse_server(server, host="0.0.0.0", port=args.port)
    else:
        mod.main()


if __name__ == "__main__":
    main()
