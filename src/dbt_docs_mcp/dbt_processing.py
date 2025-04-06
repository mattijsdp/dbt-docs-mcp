import warnings
from collections import defaultdict

import networkx as nx
from dbt.artifacts.schemas.catalog import CatalogArtifact, CatalogKey
from dbt.artifacts.schemas.manifest import WritableManifest
from dbt.artifacts.schemas.resources import ColumnInfo
from sqlglot import expressions as exp
from sqlglot import parse_one
from sqlglot.errors import OptimizeError, SqlglotError
from sqlglot.lineage import Node, lineage
from sqlglot.optimizer.qualify import qualify
from tqdm import tqdm

from dbt_docs_mcp.constants import CATALOG_PATH, DIALECT, MANIFEST_PATH

UNKNOWN = "UNKNOWN"


def load_manifest(manifest_path: str = MANIFEST_PATH):
    manifest = WritableManifest.read(manifest_path)
    return manifest


def load_catalog(catalog_path: str = CATALOG_PATH):
    catalog = CatalogArtifact.read(catalog_path)
    return catalog


def create_database_schema_table_mapping_from_sql(manifest: WritableManifest, schema: dict = {}) -> dict:
    """Supplement an existing schema with columns from models that don't have a catalog entry.

    If the schema already contains columns for a model, it will not change it.
    Args:
        manifest: A WritableManifest object containing the manifest data.
        schema: A dictionary mapping from databases to schemas to tables to columns.

    Returns:
        A dictionary mapping from databases to schemas to tables to columns.
    """
    for model in tqdm(manifest.nodes.values()):
        if (
            schema.get(model.database.lower(), {}).get(model.schema.lower(), {}).get(model.name.lower(), None)
            is not None
        ):
            continue
        expression = parse_one(model.compiled_code, dialect=DIALECT)
        try:
            qualified_expression = qualify(
                expression,
                schema=schema,
                validate_qualify_columns=False,
                allow_partial_qualification=False,
                dialect=DIALECT,
            )
        except OptimizeError as e:
            warnings.warn(
                f"Error qualifying columns for {model.unique_id}: {e}. Performing partial",
                "qualification without validation.",
                UserWarning,
            )
            qualified_expression = qualify(
                expression,
                schema=schema,
                validate_qualify_columns=True,
                allow_partial_qualification=True,
                dialect=DIALECT,
            )
        schema[model.database.lower()][model.schema.lower()][model.name.lower()] = {
            name.lower(): None for name in qualified_expression.named_selects
        }

    return schema


def create_database_schema_table_column_mapping(manifest: WritableManifest, catalog: CatalogArtifact) -> dict:
    """Returns a nested dictionary mapping from databases to schemas to tables to columns, for both nodes and sources.

    Args:
        manifest: A WritableManifest object containing the manifest data.
        catalog: A CatalogArtifact object containing the catalog data.

    Returns:
        A nested dictionary mapping from databases to schemas to tables to columns.
    """
    result = defaultdict(lambda: defaultdict(dict))

    # Process both nodes and sources which have the same structure
    for collection in [catalog.nodes, catalog.sources]:
        for _, table in collection.items():
            database = table.metadata.database.lower() or ""
            schema = table.metadata.schema.lower()
            table_name = table.metadata.name.lower()

            if database not in result:
                result[database] = defaultdict(dict)
            if schema not in result[database]:
                result[database][schema] = {}

            # Add columns to the mapping
            result[database][schema][table_name] = {k.lower(): v.type.lower() for k, v in table.columns.items()}

    # Some table aren't in the catalog e.g. ephemeral tables (and others not sure why?)
    result = create_database_schema_table_mapping_from_sql(manifest, result)

    return result


def get_parent_nodes_from_lineage_node(node: Node) -> list[Node]:
    """Get the parent nodes from a lineage node.

    Args:
        node: A lineage node.

    Returns:
        A list of parent nodes.
    """
    parent_nodes = []
    for int_node in node.walk():
        if isinstance(int_node.source, exp.Table):
            parent_nodes.append(int_node)
    return parent_nodes


def get_column_lineage(column_name: str, sql: str, schema: dict, dialect: str = DIALECT) -> list[dict]:
    """Get the lineage of a column.

    Args:
        column_name: The name of the column.
        sql: The SQL code of the model.
        schema: The schema of the model.
        dialect: The dialect of the SQL code.

    Returns:
        A list of parent nodes with their column_name and database_fqn.
    """
    lineage_node = lineage(column_name, sql=sql, schema=schema, dialect=dialect)
    parent_nodes = get_parent_nodes_from_lineage_node(lineage_node)
    column_lineage = []
    for parent_node in parent_nodes:
        column_lineage.append(
            {
                "column_name": parent_node.name.split(".")[-1].lower(),
                "database_fqn": (
                    f"{parent_node.source.catalog}.{parent_node.source.db}.{parent_node.source.this}".lower()
                ),
            }
        )
    return column_lineage


def get_column_lineage_for_model(model, schema: dict, dialect: str = DIALECT) -> dict[str, list[dict]]:
    sql = model.compiled_code
    table_column_lineage = {}
    for column_name in schema[model.database.lower()][model.schema.lower()][model.name.lower()]:
        try:
            table_column_lineage[column_name] = get_column_lineage(column_name, sql, schema, dialect)
        except SqlglotError as e:
            warnings.warn(f"Error getting column lineage for model {model.unique_id}, column {column_name}: {e}")
            table_column_lineage[column_name] = [{"column_name": UNKNOWN, "database_fqn": UNKNOWN}]
    return table_column_lineage


def get_column_lineage_for_manifest(
    manifest: WritableManifest, schema: dict, dialect: str = DIALECT
) -> dict[str, dict[str, list[dict]]]:
    manifest_column_lineage = {}
    for model_unique_id, model in tqdm(manifest.nodes.items()):
        if model.resource_type not in ["model", "test"]:
            continue
        table_column_lineage = get_column_lineage_for_model(model, schema, dialect)
        manifest_column_lineage[model_unique_id] = table_column_lineage
    return manifest_column_lineage


def get_dbt_graph(manifest: WritableManifest, schema: dict) -> nx.DiGraph:
    """Get the dbt graph from a manifest.

    The graph includes nodes, sources and exposures.
    """
    G = nx.DiGraph()
    nodes, edges = [], []
    for k, v in {**manifest.nodes, **manifest.sources, **manifest.exposures}.items():
        if v.resource_type != "exposure":
            v.columns = {
                column_name: ColumnInfo(name=column_name, data_type=data_type)
                for column_name, data_type in schema[v.database.lower()][v.schema.lower()][v.alias.lower()].items()
            }
        nodes.append((k, vars(v)))
        depends_on_nodes = getattr(getattr(v, "depends_on", {}), "nodes", [])
        edges.extend((d, k) for d in depends_on_nodes)
    G.add_nodes_from(nodes)
    G.add_edges_from(edges)
    return G


def get_column_lineage_graph(manifest_column_lineage, node_map, source_map) -> nx.DiGraph:
    """Get the column lineage graph from a manifest and a node map and source map.

    Edges represent whether a column depends on another column.
    """
    G_col = nx.DiGraph()
    nodes, edges = [], []
    for model_unique_id, table_column_lineage in manifest_column_lineage.items():
        for column_name, column_lineage in table_column_lineage.items():
            column_unique_id = f"{model_unique_id}.{column_name}"
            nodes.append((column_unique_id, {}))
            for parent_column in column_lineage:
                if parent_column["database_fqn"] == UNKNOWN:
                    continue
                parent_catalog_key = CatalogKey(*parent_column["database_fqn"].split("."))
                if parent_catalog_key not in node_map and parent_catalog_key not in source_map:
                    warnings.warn(
                        f"Model {model_unique_id} has a column {column_name} with a parent "
                        f"{parent_column['database_fqn']} that is not in the node_map or source_map"
                    )
                    continue
                parent_dbt_unique_id = node_map.get(parent_catalog_key) or list(source_map.get(parent_catalog_key))[0]
                parent_unique_id = f"{parent_dbt_unique_id}.{parent_column['column_name']}"
                edges += [(parent_unique_id, column_unique_id)]
    G_col.add_nodes_from(nodes)
    G_col.add_edges_from(edges)
    return G_col
