from dataclasses import dataclass
from typing import Optional
from .rewrite import *
from .utils import flatten


class TreeGrammar(Term):
    pass


# This is here to avoid circular imports. TODO: cleanup.
from lexing.token import Token  # noqa: E402

Symbol = str


@dataclass(frozen=True)
class EmptySet(TreeGrammar):
    pass


@dataclass(frozen=True)
class Application(TreeGrammar):
    f: Symbol
    children: tuple[TreeGrammar]
    focus: Optional[int]  # Index of the focus child, if any

    def subterms(self):
        return self.children

    def compact(self, full=False):
        check_empty = is_empty if full else lambda p: isinstance(p, EmptySet)
        if any(check_empty(c) for c in self.children):
            return EmptySet()
        return self

    @classmethod
    def of(cls, f: Symbol, *children, focus=None):
        # TODO: handle focus properly?
        flattened = flatten(children, tuple)
        return cls(f, flattened, focus).compact(full=False)

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
        if len(new_children) == 1:
            return next(iter(new_children))
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
        case Token():
            return True
        case Application(_, children):
            return all(is_nonempty(c) for c in children)
        case Union(children):
            return any(is_nonempty(c) for c in children)
        case _:
            raise TypeError(f"Unexpected type: {type(t)}")


def is_empty(t: TreeGrammar) -> bool:
    return not is_nonempty(t)


# TODO: there may be a less hacky way to do this
@fixpoint(EmptySet)
def expand_tree_grammar(t: TreeGrammar) -> TreeGrammar:
    """
    Removes Var subterms from the TreeGrammar term due to the @fixpoint.
    """
    assert isinstance(t, TreeGrammar)
    match t:
        case Union(children):
            return Union.of(expand_tree_grammar(child) for child in children)
        case Application(op, children):
            return Application.of(
                op, tuple(expand_tree_grammar(child) for child in children)
            )
        case _:
            return t
