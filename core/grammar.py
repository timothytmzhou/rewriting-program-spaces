from dataclasses import dataclass
from typing import Optional
from functools import lru_cache
from .rewrite import *
from .utils import flatten


@dataclass(frozen=True, kw_only=True)
class TreeGrammar(Term):
    is_tree: bool = False


# This is here to avoid circular imports. TODO: cleanup.
from .lexing.token import Token  # noqa: E402

Symbol = str


@dataclass(frozen=True)
class EmptySet(TreeGrammar):
    pass


@dataclass(frozen=True)
class Application(TreeGrammar):
    f: Symbol
    children: tuple[TreeGrammar, ...]

    def subterms(self):
        return self.children

    def compact(self, full=False):
        check_empty = is_empty if full else lambda p: isinstance(p, EmptySet)
        if any(check_empty(c) for c in self.children):
            return EmptySet()
        return self

    @classmethod
    def of(cls, f: Symbol, *children, is_tree: bool = False):
        flattened: tuple[TreeGrammar] = flatten(children, tuple)
        return cls(f, flattened, is_tree=is_tree).compact(full=False)

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


def _as_tree(v: Var | TreeGrammar) -> Optional[TreeGrammar]:
    t = v
    while not isinstance(t, TreeGrammar):
        t = rewriter.equations[t]  # type: ignore
    if not t.is_tree:
        return None
    match t:
        case Union(children):
            raise ValueError
        case Application(f, children):
            return Application.of(
                f,
                (as_tree(c) for c in children),
                is_tree=True,
            )
        case Token():
            return t
        case EmptySet():
            return None
        case _:
            raise ValueError


@lru_cache(maxsize=None)
def as_tree(v: Var | TreeGrammar) -> Optional[TreeGrammar]:
    return _as_tree(v)
