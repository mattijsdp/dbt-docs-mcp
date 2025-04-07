import argparse
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from dbt_docs_mcp.constants import MANIFEST_CL_PATH, MANIFEST_PATH, SCHEMA_MAPPING_PATH
from dbt_docs_mcp.tools import get_dbt_tools


def parse_args():
    parser = argparse.ArgumentParser(
        description="""DBT Docs MCP Server: A tool for exploring DBT documentation and lineage.
        If you have not yet created a manifest_column_lineage.json file or a schema_mapping.json file,
        you can use the following command: python scripts/create_manifest_cl.py
        If you have (with standard defaults) then you can simply run:
        mcp run mcp_server.py
        """,
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("--manifest-path", default=MANIFEST_PATH, help="Path to the manifest file")
    parser.add_argument("--schema-mapping-path", default=SCHEMA_MAPPING_PATH, help="Path to the schema mapping file")
    parser.add_argument("--manifest-cl-path", default=MANIFEST_CL_PATH, help="Path to the manifest column lineage file")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()

    # Check that required files exist
    missing_files = [
        f for f in [args.manifest_path, args.schema_mapping_path, args.manifest_cl_path] if not Path(f).exists()
    ]
    if missing_files:
        raise FileNotFoundError(
            f"Required file(s) not found: {', '.join(missing_files)}.\n"
            "Please run 'python scripts/create_manifest_cl.py' first to generate the required files."
        )

    # Create an MCP server
    mcp = FastMCP("DBT Docs")

    tools = get_dbt_tools(
        manifest_path=args.manifest_path,
        schema_mapping_path=args.schema_mapping_path,
        manifest_cl_path=args.manifest_cl_path,
    )

    for tool in tools:
        mcp.add_tool(tool)

    mcp.run()
