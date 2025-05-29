from collections.abc import Iterable
from networkx import DiGraph


def flatten(args, container):
    if len(args) == 1 and isinstance(args[0], Iterable):
        return container(args[0])
    return container(args)


def replace_adjacency_list(G: DiGraph, node, new_neighbors):
    old = set(G.successors(node))
    new = set(new_neighbors)
    G.remove_edges_from((node, neighbor) for neighbor in old - new)
    G.add_edges_from((node, neighbor) for neighbor in new - old)
