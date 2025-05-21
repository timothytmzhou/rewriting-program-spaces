from __future__ import annotations
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Iterable, Optional, TypeVar
from networkx import DiGraph
from contextlib import contextmanager
from collections import deque
import networkx as nx

T = TypeVar('T')


class Term:
    # TODO: define subterms using init_subclass instead of making the user do it manually
    def subterms(self) -> Iterable[Term]:
        return set()

    def _var_descendents(self) -> Iterable[Var]:
        worklist = deque([self])
        while worklist:
            current = worklist.pop()
            if isinstance(current, Term):
                worklist.extend(current.subterms())
            elif isinstance(current, Var):
                yield current

    def compact(self):
        return self


@dataclass(frozen=True)
class Var: # should not subclass Term here since we want mypy to distinguish
    f: Callable
    args: tuple

    def expand(self) -> Term:
        expanded_args = [
            arg.expand() if isinstance(arg, Var) else arg
            for arg in self.args
        ]
        assert not any(isinstance(arg, Var)
                       for arg in expanded_args), "rewrite with non-value RHS detected"
        term = self.f(*expanded_args)
        assert isinstance(term, Term)
        return term

    def __str__(self):
        return f"{self.f.__name__}({', '.join(str(arg) for arg in self.args)})"


class RewriteSystem:
    equations: dict[Var, Term]
    fix_cache: dict[tuple[Callable, Var], Any]
    dependencies: DiGraph
    worklist: deque[Var]

    def __init__(self):
        self.dependencies = DiGraph()
        self.equations = {}
        self.worklist = deque()
        self.fix_cache = {}

    def clear(self):
        self.dependencies.clear()
        self.equations.clear()
        self.worklist.clear()
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


# TODO: need to update dependency generation so we can update during compaction.

def rewrite(f):
    """
    Rewrite a (infinitely recursive) function into a capsule of equations.
    """
    def start_rewrite(start_var: Var) -> Var:
        assert not rewriter.worklist
        rewriter.worklist.append(start_var)
        to_compact = []
        while rewriter.worklist:
            current = rewriter.worklist.pop()
            if current in rewriter.equations:
                continue
            term = current.expand()
            rewriter.equations[current] = term
            for dep in term._var_descendents():
                rewriter.dependencies.add_edge(current, dep)
            to_compact.append(current)

        # simplify the equations
        for var in to_compact:
            term = rewriter.equations[var]
            assert isinstance(term, Term)
            rewriter.equations[var] = term.compact()
        return start_var

    def visit(var: Var) -> Var:
        rewriter.worklist.append(var)
        return var

    @wraps(f)
    def apply(*args) -> Var:
        # TODO: could cache less
        var = Var(f, args)
        if doing_rewrite:
            return visit(var)
        with rewriting():
            return start_rewrite(var)
    return apply


def _fixpoint(f: Callable[[Term], T], bot: Callable[..., T]) -> Callable[[Term], T]:
    """
    Kildall's algorithm for computing LFPs of functions on cyclic terms.
    """
    def kildall(start: Var) -> T:
        worklist: deque[Var] = deque()
        nodes: set[Var] = set()
        for var in nx.dfs_postorder_nodes(rewriter.dependencies, start):
            nodes.add(var)
            if (f, var) not in rewriter.fix_cache:
                worklist.append(var)
                rewriter.fix_cache[(f, var)] = bot()
        while worklist:
            current = worklist.pop()
            current_term = rewriter.equations[current]
            assert isinstance(current_term, Term)
            new = f(current_term)
            if new != rewriter.fix_cache[(f, current)]:
                rewriter.fix_cache[(f, current)] = new
                for pred in rewriter.dependencies.predecessors(current):
                    if pred not in worklist and pred in nodes:
                        worklist.append(pred)
        # assert len(rewriter.fix_cache) == len(rewriter.equations)
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


fixpoint = lambda bot: lambda f: _fixpoint(f, bot)
