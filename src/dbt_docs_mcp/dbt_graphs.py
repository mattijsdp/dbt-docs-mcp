import warnings

import networkx as nx
from dbt.artifacts.resources import ColumnInfo
from dbt.artifacts.schemas.catalog import CatalogKey
from dbt.artifacts.schemas.manifest import WritableManifest
from dbt.task.docs.generate import get_unique_id_mapping

from dbt_docs_mcp.constants import UNKNOWN
from dbt_docs_mcp.utils import load_manifest, read_json


def get_dbt_graph(manifest: WritableManifest, schema: dict) -> nx.DiGraph:
    """Get the dbt graph from a manifest.

    The graph includes nodes, sources and exposures.
    """
    G = nx.DiGraph()
    nodes, edges = [], []
    for k, v in {**manifest.nodes, **manifest.sources, **manifest.exposures}.items():
        if v.resource_type != "exposure":
            alias = getattr(v, "alias", None)
            identifier = getattr(v, "identifier", None)
            table = alias or identifier
            try:
                v.columns = {
                    column_name: ColumnInfo(name=column_name, data_type=data_type)
                    for column_name, data_type in schema[v.database.lower()][v.schema.lower()][table].items()
                }
            except KeyError:
                warnings.warn(
                    f"Node {k} cannot be found in the schema with path: {v.database.lower()}.{v.schema.lower()}.{table}"
                )

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


def get_G_and_G_col(
    manifest_path: str,
    schema_mapping_path: str,
    manifest_cl_path: str,
) -> tuple[nx.DiGraph, nx.DiGraph]:
    manifest = load_manifest(manifest_path)
    schema_mapping = read_json(schema_mapping_path)
    G = get_dbt_graph(manifest=manifest, schema=schema_mapping)

    if manifest_cl_path:
        manifest_column_lineage = read_json(manifest_cl_path)
        node_map, source_map = get_unique_id_mapping(manifest)
        G_col = get_column_lineage_graph(
            manifest_column_lineage=manifest_column_lineage, node_map=node_map, source_map=source_map
        )
    else:
        G_col = None

    return G, G_col
