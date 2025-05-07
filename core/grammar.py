from dataclasses import dataclass
from .rewrite import *
from .utils import flatten
from typing import Iterable

Symbol = str


class TreeGrammar(Term):
    pass


@dataclass(frozen=True)
class Constant[T](TreeGrammar):
    c: T


@dataclass(frozen=True)
class EmptySet(TreeGrammar):
    pass


@dataclass
class Application(TreeGrammar):
    f: Symbol
    children: tuple[TreeGrammar]

    def __init__(self, f: Symbol, *children):
        self.f = f
        self.children = flatten(children, tuple)

    def __hash__(self):
        return hash((self.f, self.children))


@dataclass
class Union(TreeGrammar):
    children: frozenset[TreeGrammar]

    def __init__(self, *children):
        self.children = flatten(children, frozenset)

    def __hash__(self):
        return hash(self.children)


@fixpoint(lambda: False)
def is_nonempty(t: TreeGrammar) -> bool:
    match t:
        case EmptySet():
            return False
        case Constant(c):
            return True
        case Application(_, children):
            return all(is_nonempty(c) for c in children)
        case Union(children):
            return any(is_nonempty(c) for c in children)
        case _:
            raise TypeError(f"Unexpected type: {type(t)}")
