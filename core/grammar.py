from dataclasses import dataclass
from lexing.leaves import Leaf
from .rewrite import *
from .utils import flatten

Symbol = str


class TreeGrammar(Term):
    pass


@dataclass(frozen=True)
class Constant(TreeGrammar):
    c: Leaf

    def __str__(self):
        return f"Constant({self.c})"


@dataclass(frozen=True)
class EmptySet(TreeGrammar):
    pass


@dataclass(frozen=True)
class Application(TreeGrammar):
    f: Symbol
    children: tuple[TreeGrammar]

    def subterms(self):
        return self.children

    def compact(self, full=False):
        check_empty = is_empty if full else lambda p: isinstance(p, EmptySet)
        if any(check_empty(c) for c in self.children):
            return EmptySet()
        return self

    @classmethod
    def of(cls, f: Symbol, *children):
        flattened = flatten(children, tuple)
        return cls(f, flattened).compact(full=False)

    def __str__(self):
        return f"{self.f}({', '.join(str(c) for c in self.children)})"


@dataclass(frozen=True)
class Union(TreeGrammar):
    children: frozenset[TreeGrammar]

    def subterms(self):
        return self.children

    def compact(self, full=False):
        check_empty = is_empty if full else lambda p: isinstance(p, EmptySet)
        new_children = frozenset(c for c in self.children if not check_empty(c))
        return Union(new_children) if new_children else EmptySet()

    @classmethod
    def of(cls, *children):
        flattened = flatten(children, frozenset)
        return cls(flattened).compact()

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


def is_empty(t: TreeGrammar) -> bool:
    return not is_nonempty(t)
