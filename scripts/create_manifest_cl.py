"""Script to generate and save column-level lineage for the entire manifest.
cl: column lineage
"""

import argparse
from pathlib import Path

from dbt_docs_mcp.constants import (
    CATALOG_PATH,
    MANIFEST_CL_PATH,
    MANIFEST_PATH,
    SCHEMA_MAPPING_PATH,
)
from dbt_docs_mcp.dbt_processing import (
    read_or_write_manifest_column_lineage,
    read_or_write_schema_mapping,
)
from dbt_docs_mcp.utils import load_catalog, load_manifest


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
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite the existing manifest column lineage JSON",
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
    print(args.overwrite)
    manifest = load_manifest(args.manifest_path)
    catalog = load_catalog(args.catalog_path)

    schema_mapping = read_or_write_schema_mapping(manifest, catalog, args.schema_mapping_path, args.overwrite)

    _ = read_or_write_manifest_column_lineage(manifest, schema_mapping, args.manifest_cl_path, args.overwrite)

    print("Done!")


if __name__ == "__main__":
    main()
