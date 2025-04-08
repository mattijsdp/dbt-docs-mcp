import json

from dbt.artifacts.schemas.catalog import CatalogArtifact
from dbt.artifacts.schemas.manifest import WritableManifest

from dbt_docs_mcp.constants import CATALOG_PATH, MANIFEST_PATH


def write_json(json_data, file_path):
    with open(file_path, "w") as f:
        json.dump(json_data, f, indent=4)


def read_json(file_path):
    with open(file_path, "r") as f:
        return json.load(f)


def load_manifest(manifest_path: str = MANIFEST_PATH):
    manifest = WritableManifest.read(manifest_path)
    return manifest


def load_catalog(catalog_path: str = CATALOG_PATH):
    catalog = CatalogArtifact.read(catalog_path)
    return catalog
