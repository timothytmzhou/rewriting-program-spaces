from functools import wraps
from networkx import DiGraph, is_isomorphic
from core.rewrite import *


def reset(test_function):
    """
    Decorator for tests which clears the state of the TRS before running the test.
    """
    @wraps(test_function)
    def wrapper(*args, **kwargs):
        rewriter.clear()
        test_function(*args, **kwargs)
    return wrapper


def dependencies_isomorphic_to(G: DiGraph):
    """
    Check if the dependencies graph is isomorphic to the given edges.
    """
    return is_isomorphic(rewriter.dependencies, G)
