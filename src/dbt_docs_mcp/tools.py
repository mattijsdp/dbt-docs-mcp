from typing import Callable, Iterable

import networkx as nx
from dbt.task.docs.generate import get_unique_id_mapping
from rapidfuzz.distance import DamerauLevenshtein
from rapidfuzz.process import extract

from dbt_docs_mcp.dbt_processing import get_column_lineage_graph, get_dbt_graph, load_manifest
from dbt_docs_mcp.utils import read_json

SCORER = DamerauLevenshtein.normalized_similarity
SCORE_CUTOFF = 0.1

NODE_RELEVANT_ATTRIBUTES = [
    "description",
    "columns",
    "relation_name",
    "resource_type",
    "path",
    "unique_id",
    "tags",
    "metrics",
    "compiled_code",
]
RELEVENT_ATTRIBUTES = {
    "model": NODE_RELEVANT_ATTRIBUTES,
    "source": ["description", "columns", "relation_name", "resource_type", "path", "unique_id", "tags"],
    "exposure": ["description", "resource_type", "type", "owner", "path", "unique_id", "tags", "metrics"],
    "test": NODE_RELEVANT_ATTRIBUTES,
    "seed": NODE_RELEVANT_ATTRIBUTES,
    "operation": NODE_RELEVANT_ATTRIBUTES,
    "snapshot": NODE_RELEVANT_ATTRIBUTES,
}


def get_useful_attributes(dbt_unique_id: str, G: nx.DiGraph):
    attributes = G.nodes[dbt_unique_id]
    # Return everything if resource_type not one of the main ones
    if attributes["resource_type"] not in RELEVENT_ATTRIBUTES:
        return attributes
    return {key: attributes[key] for key in RELEVENT_ATTRIBUTES[attributes["resource_type"]]}


def get_useful_attributes_for_models(dbt_unique_ids: Iterable[str], G: nx.DiGraph):
    return {dbt_unique_id: get_useful_attributes(dbt_unique_id, G) for dbt_unique_id in dbt_unique_ids}


def get_dbt_node_attributes_tool(G: nx.DiGraph):
    def get_dbt_node_attributes(dbt_unique_id: str):
        """Get attributes of a given node.

        Args:
            dbt_unique_id (str): The dbt unique id of the node to get attributes for

        Returns:
            dict: Dictionary containing model attributes:
                - description: Model description
                - depends_on: List of models this model depends on
                - columns: Dictionary of column names and their descriptions
                - compiled_code: The compiled SQL code for the model

        """
        return get_useful_attributes(dbt_unique_id, G)

    return get_dbt_node_attributes


def get_dbt_predecessor_tool(G: nx.DiGraph):
    def get_dbt_predecessors(dbt_unique_id: str):
        """Get the predecessor nodes of a given node. Returns a list of dbt unique ids.

        To get a node's attributes, use the get_dbt_node_attributes tool. Predecessors are nodes that are directly
        upstream of the given node (i.e. only one edge away).

        Args:
            dbt_unique_id (str): The dbt unique id of the node to get predecessors for

        Returns:
            list: List of dbt unique ids. To get their attributes, use the get_dbt_node_attributes tool.

        """
        predecessor_nodes = list(G.predecessors(dbt_unique_id))
        return predecessor_nodes

    return get_dbt_predecessors


def get_dbt_successor_tool(G: nx.DiGraph):
    def get_dbt_successors(dbt_unique_id: str):
        """Get the successor nodes of a given node. Returns a list of dbt unique ids.

        To get a node's attributes, use the get_dbt_node_attributes tool. Successors are nodes that are directly
        downstream of the given node (i.e. only one edge away).

        Args:
            dbt_unique_id (str): The dbt unique id of the node to get successors for

        Returns:
            list: List of dbt unique ids. To get their attributes, use the get_dbt_node_attributes tool.

        """
        successor_nodes = list(G.successors(dbt_unique_id))
        return successor_nodes

    return get_dbt_successors


def get_dbt_node_attributes_from_columns(columns: list[str], G: nx.DiGraph):
    model_attributes_for_columns = {}
    for column in columns:
        dbt_unique_id, _ = column.rsplit(".", 1)
        model_attributes_for_columns[column] = get_useful_attributes(dbt_unique_id, G)
    return model_attributes_for_columns


def get_column_ancestors_tool(G: nx.DiGraph, G_col: nx.DiGraph):
    def get_column_ancestors(dbt_unique_id: str, column_name: str) -> list[dict]:
        """Get the ancestor models for a specific column.

        Ancestors are all models that the specified column depends on, even ones that are more than one edge away.
        As such, it is a much more targeted tool and should be used over get_model_predecessors if you are interested
        in a specific column/field.

        Args:
            model_name (str): The name of the model containing the column
            column_name (str): The name of the column to get ancestors for

        Returns:
            dict: mapping of ancestor column keys in format {dbt_unique_id.column_name} to that model's attributes

        """
        ancestor_columns = nx.ancestors(G_col, f"{dbt_unique_id}.{column_name}")
        return get_dbt_node_attributes_from_columns(ancestor_columns, G)

    return get_column_ancestors


def get_column_descendants_tool(G: nx.DiGraph, G_col: nx.DiGraph):
    def get_column_descendants(dbt_unique_id: str, column_name: str):
        """Get the descendant models for a specific column.

        Descendants are all models that depend on the specified column, even ones that are more than one edge away.
        As such, it is a much more targeted tool and should be used over get_model_successors if you are interested
        in a specific column/field.

        Args:
            model_name (str): The name of the model containing the column
            column_name (str): The name of the column to get descendants for

        Returns:
            dict: mapping of ancestor column keys in format {dbt_unique_id.column_name} to that model's attributes

        """
        descendant_columns = nx.descendants(G_col, f"{dbt_unique_id}.{column_name}")
        return get_dbt_node_attributes_from_columns(descendant_columns, G)

    return get_column_descendants


def model_names_from_matches(matches: list[tuple[str, float, str]]):
    return [match[2] for match in matches]


def get_dbt_node_search_tool(G: nx.DiGraph):
    dbt_unique_ids = list(G.nodes.keys())

    def search_dbt_node_names(search_string: str, first_n: int = 10):
        """Search for dbt nodes by name. Returns a list of dbt unique ids.

        To get their attributes, use the get_dbt_node_attributes tool.
        Args:
            search_string (str): The string to search for in model names
            first_n (int, optional): Maximum number of results to return. Defaults to 10.

        Returns:
            list: List of dbt unique ids. To get their attributes, use the get_dbt_node_attributes tool.

        """
        matches = extract(
            search_string,
            dbt_unique_ids,
            limit=first_n,
            scorer=SCORER,
            score_cutoff=SCORE_CUTOFF,
        )
        matching_models = model_names_from_matches(matches)
        return matching_models

    return search_dbt_node_names


def get_dbt_column_search_tool(G: nx.DiGraph):
    column_names = {node_name: column for node_name, node in G.nodes.items() for column in node["columns"]}

    def search_dbt_column_names(search_string: str, first_n: int = 10):
        """Search for nodes containing columns matching a name pattern. Returns a list of dbt unique ids.

        To get their attributes, use the get_dbt_node_attributes tool.
        Args:
            search_string (str): The string to search for in column names
            first_n (int, optional): Maximum number of models to return. Defaults to 10.

        Returns:
            list: List of dbt unique ids. To get their attributes, use the get_dbt_node_attributes tool.

        """
        matches = extract(
            search_string,
            column_names,
            limit=first_n,
            scorer=SCORER,
            score_cutoff=SCORE_CUTOFF,
        )
        matching_models = model_names_from_matches(matches)
        return matching_models

    return search_dbt_column_names


def get_dbt_sql_search_tool(G: nx.DiGraph):
    compiled_code = {node_name: node["compiled_code"] for node_name, node in list(G.nodes.items())}

    def search_dbt_sql_code(search_string: str, first_n: int = 10):
        """Search for nodes containing a string in their SQL code. Returns a list of dbt unique ids.

        To get their attributes, use the get_dbt_node_attributes tool.
        Args:
            search_string (str): The string to search for in SQL code
            first_n (int, optional): Maximum number of results to return. Defaults to 10.

        Returns:
            list: List of dbt unique ids. To get their attributes, use the get_dbt_node_attributes tool.

        """
        matches = extract(search_string, compiled_code, limit=first_n, scorer=SCORER)
        matching_models = model_names_from_matches(matches)
        return matching_models

    return search_dbt_sql_code


def get_dbt_tools(manifest_path: str, schema_mapping_path: str, manifest_cl_path: str) -> list[Callable]:
    """Get all tools for working with the DBT graphs.

    Args:
        manifest_path (str): The path to the manifest file
        schema_mapping_path (str): The path to the schema mapping file
        manifest_cl_path (str): The path to the manifest column lineage file

    Returns:
        list: List of tool functions for working with DBT data
    """
    manifest = load_manifest(manifest_path)
    schema_mapping = read_json(schema_mapping_path)
    manifest_column_lineage = read_json(manifest_cl_path)
    node_map, source_map = get_unique_id_mapping(manifest)

    G = get_dbt_graph(manifest=manifest, schema=schema_mapping)
    G_col = get_column_lineage_graph(
        manifest_column_lineage=manifest_column_lineage, node_map=node_map, source_map=source_map
    )

    tools = [
        get_dbt_predecessor_tool(G=G),
        get_dbt_successor_tool(G=G),
        get_dbt_node_attributes_tool(G=G),
        get_dbt_node_search_tool(G=G),
        get_dbt_column_search_tool(G=G),
        get_dbt_sql_search_tool(G=G),
    ]
    if G_col is not None:
        tools.extend(
            [
                get_column_ancestors_tool(G=G, G_col=G_col),
                get_column_descendants_tool(G=G, G_col=G_col),
            ]
        )
    return tools
