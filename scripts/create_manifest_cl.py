"""Script to generate and save column-level lineage for the entire manifest.
cl: column lineage
"""

import argparse
from pathlib import Path

from dbt_docs_mcp.constants import (
    CATALOG_PATH,
    DIALECT,
    MANIFEST_CL_PATH,
    MANIFEST_PATH,
    SCHEMA_MAPPING_PATH,
)
from dbt_docs_mcp.dbt_processing import (
    create_database_schema_table_column_mapping,
    get_column_lineage_for_manifest,
    load_catalog,
    load_manifest,
)
from dbt_docs_mcp.utils import read_json, write_json


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate column-level lineage for a dbt manifest",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--manifest-path",
        type=str,
        default=MANIFEST_PATH,
        help="Path to the manifest.json file",
    )
    parser.add_argument(
        "--catalog-path",
        type=str,
        default=CATALOG_PATH,
        help="Path to the catalog.json file",
    )
    parser.add_argument(
        "--schema-mapping-path",
        type=str,
        default=SCHEMA_MAPPING_PATH,
        help="Path where to save the schema mapping JSON",
    )
    parser.add_argument(
        "--manifest-cl-path",
        type=str,
        default=MANIFEST_CL_PATH,
        help="Path where to save the manifest column lineage JSON",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Check that required files exist
    missing_files = [f for f in [args.manifest_path, args.catalog_path] if not Path(f).exists()]
    if missing_files:
        raise FileNotFoundError(
            f"Required file(s) not found: {', '.join(missing_files)}.\n"
            "These are files dbt creates."
            "Please see [link](https://docs.getdbt.com/reference/artifacts/dbt-artifacts) for more information."
        )

    # Ensure output directories exist
    Path(args.schema_mapping_path).parent.mkdir(parents=True, exist_ok=True)
    Path(args.manifest_cl_path).parent.mkdir(parents=True, exist_ok=True)

    # Load manifest and catalog
    print("Loading manifest and catalog...")
    manifest = load_manifest(args.manifest_path)
    catalog = load_catalog(args.catalog_path)

    # Load existing schema mapping if it exists
    if Path(args.schema_mapping_path).exists():
        schema_mapping = read_json(args.schema_mapping_path)
    else:
        # Create database schema table column mapping
        print("Creating database schema table column mapping...")
        schema_mapping = create_database_schema_table_column_mapping(manifest, catalog)
        write_json(schema_mapping, args.schema_mapping_path)

    # Generate column-level lineage for the entire manifest
    print("Generating column-level lineage...")
    manifest_cll = get_column_lineage_for_manifest(manifest=manifest, schema=schema_mapping, dialect=DIALECT)

    print(f"Saving results to {args.manifest_cl_path}...")
    write_json(manifest_cll, args.manifest_cl_path)

    print("Done!")


if __name__ == "__main__":
    main()
