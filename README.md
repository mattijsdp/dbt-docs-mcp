[![MseeP.ai Security Assessment Badge](https://mseep.net/pr/mattijsdp-dbt-docs-mcp-badge.png)](https://mseep.ai/app/mattijsdp-dbt-docs-mcp)

# dbt-docs-mcp

Model Context Protocol (MCP) server for interacting with dbt project metadata, including dbt Docs artifacts (`manifest.json`, `catalog.json`). This server exposes dbt graph information and allows querying node details, model/column lineage, and related metadata.

## Key Functionality

This server provides tools to:

*   **Search dbt Nodes:**
    *   Find nodes (models, sources, tests, etc.) by name (`search_dbt_node_names`).
    *   Locate nodes based on column names (`search_dbt_column_names`).
    *   Search within the compiled SQL code of nodes (`search_dbt_sql_code`).
*   **Inspect Nodes:**
    *   Retrieve detailed attributes for any given node unique ID (`get_dbt_node_attributes`).
*   **Explore Lineage:**
    *   Find direct upstream dependencies (predecessors) of a node (`get_dbt_predecessors`).
    *   Find direct downstream dependents (successors) of a node (`get_dbt_successors`).
*   **Column-Level Lineage:**
    *   Trace all upstream sources for a specific column in a model (`get_column_ancestors`).
    *   Trace all downstream dependents of a specific column in a model (`get_column_descendants`).
*   **Suggested extensions:**
    *   Tool that allows executing SQL queries.
    *   Tool that retrieves table/view/column metadata directly from the database.
    *   Tool to search knowledge-base.

## Getting Started

1.  **Prerequisites:** Ensure you have Python installed and [uv](https://docs.astral.sh/uv/)
2.  **Clone the repo:**
    ```bash
    git clone <repository-url>
    cd dbt-docs-mcp
    ```
3.  **Optional: parse dbt manifest for column-level lineage:**
    - Setup the required Python environment, e.g.:
    ```bash
    uv sync
    ```
    - Use the provided script `scripts/create_manifest_cl.py` and simply provide the path to your dbt manifest, dbt catalog and the desired output paths for your schema and column lineage file:
    ```bash
    python scripts/create_manifest_cl.py --manifest-path PATH_TO_YOUR_MANIFEST_FILE --catalog-path PATH_TO_YOUR_CATALOG_FILE --schema-mapping-path DESIRED_OUTPUT_PATH_FOR_SCHEMA_MAPPING --manifest-cl-path DESIRED_OUTPUT_PATH_FOR_MANIFEST_CL
    ```
    - Depending on your dbt project size, creating column-lineage can take a while (hours)
4.  **Run the Server:**
    - If your desired MCP client (Claude desktop, Cursor, etc.) supports mcp.json it would like as below:
    ```json
    {
        "mcpServers": {
            "DBT Docs MCP": {
            "command": "uv",
            "args": [
                "run",
                "--with",
                "networkx,mcp[cli],rapidfuzz,dbt-core,python-decouple,sqlglot,tqdm",
                "mcp",
                "run",
                "/Users/mattijs/repos/dbt-docs-mcp/src/mcp_server.py"
            ],
            "env": {
                "MANIFEST_PATH": "/Users/mattijs/repos/dbt-docs-mcp/inputs/manifest.json",
                "SCHEMA_MAPPING_PATH": "/Users/mattijs/repos/dbt-docs-mcp/outputs/schema_mapping.json",
                "MANIFEST_CL_PATH": "/Users/mattijs/repos/dbt-docs-mcp/outputs/manifest_column_lineage.json"
            }
            }
        }
    }
    ```
