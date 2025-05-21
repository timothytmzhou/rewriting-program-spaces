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

    def subterms(self):
        return self.children

    @classmethod
    def of(cls, f: Symbol, *children):
        flattened = flatten(children, tuple)
        if any(isinstance(c, EmptySet) for c in flattened):
            return EmptySet()
        return cls(f, flattened)

    def __str__(self):
        return f"{self.f}({', '.join(str(c) for c in self.children)})"


@dataclass(frozen=True)
class Union(TreeGrammar):
    children: frozenset[TreeGrammar]

    def subterms(self):
        return self.children

    @classmethod
    def of(cls, *children):
        flattened = flatten(children, frozenset) - {EmptySet()}
        if not flattened:
            return EmptySet()
        return cls(flattened)

    def __str__(self):
        return f"Union({', '.join(str(c) for c in self.children)})"


@fixpoint(lambda: False)
def is_nonempty(t: TreeGrammar) -> bool:
    match t:
        case EmptySet():
            return False
        case Constant():
            return True
        case Application(_, children):
            return all(is_nonempty(c) for c in children)
        case Union(children):
            return any(is_nonempty(c) for c in children)
        case _:
            raise TypeError(f"Unexpected type: {type(t)}")
