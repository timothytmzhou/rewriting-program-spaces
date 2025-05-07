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


@dataclass(frozen=True)
class Application(TreeGrammar):
    f: Symbol
    children: tuple[TreeGrammar]

    @classmethod
    def of(cls, f: Symbol, *children):
        return cls(f, flatten(children, tuple))


@dataclass(frozen=True)
class Union(TreeGrammar):
    children: frozenset[TreeGrammar]

    @classmethod
    def of(cls, *children):
        return cls(flatten(children, frozenset))


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
