import logging
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from dbt_docs_mcp.constants import (
    CATALOG_PATH,  # Assuming CATALOG_PATH is defined here
    MANIFEST_CL_PATH,
    MANIFEST_PATH,
    SCHEMA_MAPPING_PATH,
)
from dbt_docs_mcp.dbt_graphs import get_G_and_G_col
from dbt_docs_mcp.dbt_processing import read_or_write_schema_mapping
from dbt_docs_mcp.tools import get_dbt_tools
from dbt_docs_mcp.utils import load_catalog, load_manifest

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

"""
DBT Docs MCP Server: A tool for exploring DBT documentation and lineage.

If you have not yet created a manifest_column_lineage.json file or a schema_mapping.json file,
you can use the following command: python scripts/create_manifest_cl.py
If you have (with standard defaults) then you can simply run:
mcp run mcp_server.py

Handles different scenarios for finding input files:
1. manifest.json, schema_mapping.json, manifest_column_lineage.json exist -> Load full graphs.
2. manifest.json, schema_mapping.json exist (no col lineage) -> Load graph G, G_col=None.
3. manifest.json, catalog.json exist (no schema mapping/col lineage) -> Create schema_mapping.json, then load G, G_col=None.

Run command: mcp run mcp_server.py
"""  # noqa: E501

mcp = FastMCP("DBT Docs")

# --- File Loading Logic ---

# 1. Check essential MANIFEST_PATH first
logger.info(f"Looking for manifest file at: {MANIFEST_PATH}")
if not Path(MANIFEST_PATH).exists():
    raise FileNotFoundError(f"Required file not found: {MANIFEST_PATH}. Cannot proceed.")
logger.info("Manifest file found.")

schema_mapping_exists = Path(SCHEMA_MAPPING_PATH).exists()
manifest_cl_path_to_use = None  # Default to no column lineage

if schema_mapping_exists:
    logger.info(f"Found schema mapping file: {SCHEMA_MAPPING_PATH}")
    # Scenario 1 or 2 depends on manifest_cl_path
    if Path(MANIFEST_CL_PATH).exists():
        logger.info(f"Found column lineage file: {MANIFEST_CL_PATH}. Will load column lineage graph.")
        manifest_cl_path_to_use = MANIFEST_CL_PATH
    else:
        logger.warning(f"Column lineage file not found at: {MANIFEST_CL_PATH}. Proceeding without column lineage.")
else:
    # Schema mapping not found, check if we can create it (Scenario 3)
    logger.warning(f"Schema mapping file not found: {SCHEMA_MAPPING_PATH}")
    logger.info(f"Looking for catalog file at: {CATALOG_PATH}")
    if Path(CATALOG_PATH).exists():
        logger.info(f"Found catalog file: {CATALOG_PATH}. Attempting to create schema mapping...")
        try:
            manifest = load_manifest(MANIFEST_PATH)
            catalog = load_catalog(CATALOG_PATH)

            schema_mapping = read_or_write_schema_mapping(manifest, catalog, SCHEMA_MAPPING_PATH)

            if not Path(SCHEMA_MAPPING_PATH).exists():
                raise RuntimeError(f"Utility function failed to create schema mapping file at {SCHEMA_MAPPING_PATH}.")
            logger.info(f"Successfully created schema mapping file: {SCHEMA_MAPPING_PATH}")
            # Proceed without column lineage as it wasn't present initially
            logger.warning(
                f"Column lineage file ({MANIFEST_CL_PATH}) was not found. Proceeding without column lineage."
            )
        except Exception as e:
            logger.error(f"Error creating schema mapping file from catalog: {e}", exc_info=True)
            raise RuntimeError(f"Failed to create schema mapping file from catalog: {e}")
    else:
        # Error: Cannot proceed without schema mapping or catalog
        raise FileNotFoundError(
            f"Required file not found: {SCHEMA_MAPPING_PATH}."
            f"Also could not find catalog file to generate it: {CATALOG_PATH}."
            "Please provide a valid schema_mapping.json or ensure manifest.json and catalog.json are present."
        )

# --- Load Graphs ---
logger.info("Loading dbt graph data...")
G, G_col = get_G_and_G_col(
    manifest_path=MANIFEST_PATH,
    schema_mapping_path=SCHEMA_MAPPING_PATH,  # Should exist now or error was raised
    manifest_cl_path=manifest_cl_path_to_use,
)
logger.info("Graph loading complete.")
if G_col is None:
    logger.info("Note: Column lineage graph (G_col) was not loaded.")
else:
    logger.info("Column lineage graph (G_col) loaded successfully.")


# --- Setup MCP Server ---
mcp = FastMCP("DBT Docs")

tools = get_dbt_tools(G, G_col)  # Pass potentially None G_col

logger.info(f"Adding {len(tools)} tools to MCP server.")
for tool in tools:
    mcp.add_tool(tool)

if __name__ == "__main__":
    logger.info("Starting MCP server...")
    mcp.run()
