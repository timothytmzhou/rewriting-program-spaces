from __future__ import annotations
from matplotlib import pyplot as plt
import networkx as nx
from dataclasses import dataclass, field
from functools import wraps
from typing import Any, Callable, Iterable, TypeVar, Optional
from networkx import DiGraph
from contextlib import contextmanager
from collections import deque
from .utils import replace_adjacency_list


T = TypeVar('T')


class Term:
    def subterms(self) -> Iterable[Term]:
        return set()

    def compact(self, full=False):
        """
        Defines simplfication rules for terms.
        If full is True, one should do more extensive simplificaiton
        (e.g. with fixpoint computation). Otherwise it should be cheap.
        """
        return self


@dataclass(frozen=True)
class Var:  # should not subclass Term here since we want mypy to distinguish
    f: Callable
    args: tuple
    kwargs: dict
    _hash: int = field(init=False, repr=False)

    def __post_init__(self):
        hash_value = hash((self.f, self.args, tuple(self.kwargs.values())))
        object.__setattr__(self, '_hash', hash_value)

    def __str__(self):
        return f"{self.f.__name__}({', '.join(str(arg) for arg in self.args)})"

    def __hash__(self):
        return self._hash


def var_descendents(term: Term | Var) -> Iterable[Var]:
    match term:
        case Var():
            yield term
        case Term():
            for subterm in term.subterms():
                yield from var_descendents(subterm)


class RewriteSystem:
    equations: dict[Var, Term]
    fix_cache: dict[tuple[Callable, Var], Any]
    dependencies: DiGraph
    worklist: deque[Var]

    def __init__(self):
        self.dependencies = DiGraph()
        self.equations = {}
        self.fix_cache = {}

    def clear(self):
        self.dependencies.clear()
        self.equations.clear()
        self.fix_cache.clear()

    def __str__(self):
        equations = "\n".join(
            f"{var} = {term}"
            for var, term in self.equations.items()
        )
        fix_cache = "\n".join(
            f"{f.__name__}({var}) = {result}"
            for (f, var), result in self.fix_cache.items()
        )
        return f"Equations:\n{equations}\n\nFixpoint Cache:\n{fix_cache}"


rewriter = RewriteSystem()  # not super thread safe
doing_rewrite: bool = False


@contextmanager
def rewriting():
    global doing_rewrite
    try:
        doing_rewrite = True
        yield
    finally:
        doing_rewrite = False


def rewrite(f):
    """
    Rewrite a (infinitely recursive) function into a capsule of equations.
    """
    def simplify(start: Var):
        worklist = deque([start])
        visited = set()
        while worklist:
            var = worklist.popleft()
            term = rewriter.equations[var]
            while isinstance(term, Var):
                term = rewriter.equations[term]
            compacted = term.compact(full=True)
            rewriter.equations[var] = compacted
            descendents = set(var_descendents(compacted))
            replace_adjacency_list(rewriter.dependencies, var, descendents)
            visited.add(var)
            worklist.extend(set(descendents) - visited)

    def start_rewrite(start_var: Var) -> Var:
        worklist: deque[Var] = deque([start_var])
        while worklist:
            current = worklist.popleft()
            if (
                current in rewriter.equations or
                current in rewriter.dependencies and rewriter.dependencies.in_degree(
                    current) == 0
            ):
                continue
            unprocessed = [
                arg for arg in current.args
                if isinstance(arg, Var) and arg not in rewriter.equations
            ]
            if unprocessed:
                worklist.appendleft(current)
                worklist.extendleft(unprocessed)
                continue

            expanded_args = []
            for arg in current.args:
                while isinstance(arg, Var):
                    arg = rewriter.equations[arg]
                expanded_args.append(arg)

            term = current.f(*expanded_args, **current.kwargs)
            rewriter.equations[current] = term
            rewriter.dependencies.add_node(current)
            descendents = list(var_descendents(term))
            rewriter.dependencies.add_edges_from(
                (current, dep) for dep in descendents
            )
            worklist.extend(descendents)

        simplify(start_var)
        return start_var

    @wraps(f)
    def apply(*args, **kwargs) -> Var:
        var = Var(f, args, kwargs)
        if doing_rewrite:
            return var
        with rewriting():
            return start_rewrite(var)
    return apply


def _fixpoint(f: Callable[[Term], T], bot: Callable[..., T]) -> Callable[[Term], T]:
    """
    Kildall's algorithm for computing LFPs of functions on cyclic terms.
    """
    def kildall(start: Var) -> T:
        if (f, start) in rewriter.fix_cache:
            return rewriter.fix_cache[(f, start)]
        worklist: deque[Var] = deque()
        nodes: set[Var] = set()
        for var in nx.dfs_postorder_nodes(rewriter.dependencies, start):
            if (f, var) not in rewriter.fix_cache:
                nodes.add(var)
                worklist.append(var)
                rewriter.fix_cache[(f, var)] = bot()
        while worklist:
            current = worklist.popleft()
            current_term = rewriter.equations[current]
            while isinstance(current_term, Var):
                current_term = rewriter.equations[current_term]
            assert isinstance(current_term, Term)
            new = f(current_term)
            if new != rewriter.fix_cache[(f, current)]:
                rewriter.fix_cache[(f, current)] = new
                for pred in rewriter.dependencies.predecessors(current):
                    if pred not in worklist and pred in nodes:
                        worklist.append(pred)
        return rewriter.fix_cache[(f, start)]

    @wraps(f)
    def apply(t: Term) -> T:
        if (f, t) in rewriter.fix_cache:
            assert isinstance(t, Var)
            return rewriter.fix_cache[(f, t)]
        elif not isinstance(t, Var):
            return f(t)
        else:
            return kildall(t)

    return apply


def fixpoint(bot): return lambda f: _fixpoint(f, bot)
