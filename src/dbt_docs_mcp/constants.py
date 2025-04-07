from decouple import config

MANIFEST_PATH = config("MANIFEST_PATH", default="inputs/manifest.json")
CATALOG_PATH = config("CATALOG_PATH", default="inputs/catalog.json")
SCHEMA_MAPPING_PATH = config("SCHEMA_MAPPING_PATH", default="outputs/schema_mapping.json")
MANIFEST_CL_PATH = config("MANIFEST_CL_PATH", default="outputs/manifest_column_lineage.json")

DIALECT = config("DIALECT", default="snowflake")
