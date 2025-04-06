"""Script to generate and save column-level lineage for the entire manifest.
cll: column level lineage
"""

import argparse
from pathlib import Path

from dbt_docs_mcp.constants import CATALOG_PATH, DIALECT, MANIFEST_PATH
from dbt_docs_mcp.dbt_processing import (
    create_database_schema_table_column_mapping,
    get_column_lineage_for_manifest,
    load_catalog,
    load_manifest,
)
from dbt_docs_mcp.utils import read_json, write_json


def parse_args():
    parser = argparse.ArgumentParser(description="Generate column-level lineage for a dbt manifest")
    parser.add_argument(
        "--manifest-path",
        type=str,
        default=MANIFEST_PATH,
        help="Path to the manifest.json file (default: from constants.py)",
    )
    parser.add_argument(
        "--catalog-path",
        type=str,
        default=CATALOG_PATH,
        help="Path to the catalog.json file (default: from constants.py)",
    )
    parser.add_argument(
        "--output-dir", type=str, default="outputs", help="Path where to save the output JSON (default: outputs)"
    )
    return parser.parse_args()


def main():
    args = parse_args()

    # Load manifest and catalog
    print("Loading manifest and catalog...")
    manifest = load_manifest(args.manifest_path)
    catalog = load_catalog(args.catalog_path)

    # Save the results
    output_path = Path(args.output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    # Load existing schema mapping if it exists
    schema_mapping_path = output_path / "schema_mapping.json"
    if schema_mapping_path.exists():
        schema_mapping = read_json(schema_mapping_path)
    else:
        # Create database schema table column mapping
        print("Creating database schema table column mapping...")
        schema_mapping = create_database_schema_table_column_mapping(manifest, catalog)
        write_json(schema_mapping, schema_mapping_path)

    # Generate column-level lineage for the entire manifest
    print("Generating column-level lineage...")
    manifest_cll = get_column_lineage_for_manifest(manifest=manifest, schema=schema_mapping, dialect=DIALECT)

    print(f"Saving results to {output_path}...")
    write_json(manifest_cll, output_path / "manifest_column_lineage.json")

    print("Done!")


if __name__ == "__main__":
    main()
