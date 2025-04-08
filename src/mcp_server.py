import sys
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from dbt_docs_mcp.constants import MANIFEST_CL_PATH, MANIFEST_PATH, SCHEMA_MAPPING_PATH
from dbt_docs_mcp.tools import get_dbt_tools

"""
DBT Docs MCP Server: A tool for exploring DBT documentation and lineage.
If you have not yet created a manifest_column_lineage.json file or a schema_mapping.json file,
you can use the following command: python scripts/create_manifest_cl.py
If you have (with standard defaults) then you can simply run:
mcp run mcp_server.py
"""

mcp = FastMCP("DBT Docs")

# Check that required files exist
missing_files = [f for f in [MANIFEST_PATH, SCHEMA_MAPPING_PATH, MANIFEST_CL_PATH] if not Path(f).exists()]
if missing_files:
    raise FileNotFoundError(
        f"Required file(s) not found: {', '.join(missing_files)}.\n"
        "Please run 'python scripts/create_manifest_cl.py' first to generate the required files."
    )

# Create an MCP server
mcp = FastMCP("DBT Docs")

tools = get_dbt_tools(
    manifest_path=MANIFEST_PATH,
    schema_mapping_path=SCHEMA_MAPPING_PATH,
    manifest_cl_path=MANIFEST_CL_PATH,
)
print(tools, file=sys.stderr)

for tool in tools:
    mcp.add_tool(tool)
