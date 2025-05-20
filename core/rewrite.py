from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional, TypeVar
from networkx import DiGraph
from contextlib import contextmanager
from collections import deque
import networkx as nx

T = TypeVar('T')


class Term:
    def compact(self):
        return self


@dataclass(frozen=True)
class Var:
    f: Callable
    args: tuple

    def expand(self):
        expanded_args = (
            arg.expand() if isinstance(arg, Var) else arg
            for arg in self.args
        )
        return self.f(*expanded_args)

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
        return "\n".join(
            f"{var} = {term}"
            for var, term in self.equations.items()
        )


rewriter = RewriteSystem()  # not super thread safe
doing_rewrite: bool = False
doing_fixpoint: bool = False
origin: Optional[Var] = None


@contextmanager
def rewriting():
    global doing_rewrite
    try:
        doing_rewrite = True
        yield
    finally:
        doing_rewrite = False


@contextmanager
def fixpointing():
    global doing_fixpoint
    try:
        doing_fixpoint = True
        yield
    finally:
        doing_fixpoint = False

# TODO: need to update dependency generation so we can update during compaction.


def set_origin(new_origin: Var):
    global origin
    origin = new_origin


def rewrite(f):
    """
    Rewrite a (infinitely recursive) function into a capsule of equations.
    """
    def start_rewrite(start_var: Var) -> Term:
        assert not rewriter.worklist
        rewriter.worklist.append(start_var)
        to_compact = []
        while rewriter.worklist:
            current = rewriter.worklist.pop()
            if current in rewriter.equations:
                continue
            set_origin(current)
            rewriter.equations[current] = current.expand()
            to_compact.append(current)

        # simplify the equations
        for var in to_compact:
            term = rewriter.equations[var]
            assert isinstance(term, Term)
            rewriter.equations[var] = term.compact()
        return rewriter.equations[start_var]

    def visit(var: Var) -> Var:
        rewriter.worklist.append(var)
        rewriter.dependencies.add_edge(origin, var)
        return var

    @wraps(f)
    def apply(*args) -> Var | Term:
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
        # initialize fixpoint cache with anything we don't know the value of already
        uncomputed = [
            var for var in nx.dfs_postorder_nodes(rewriter.dependencies, start)
            if (f, var) not in rewriter.fix_cache
        ]
        worklist = deque(uncomputed)
        for var in uncomputed:
            rewriter.fix_cache[(f, var)] = bot()
        while worklist:
            current = worklist.pop()
            current_term = rewriter.equations[current]
            assert isinstance(current_term, Term)
            new = f(current_term)
            if new != rewriter.fix_cache[(f, current)]:
                rewriter.fix_cache[(f, current)] = new
                for pred in rewriter.dependencies.predecessors(current):
                    if pred not in worklist:
                        worklist.append(pred)
        return rewriter.fix_cache[(f, start)]

    @wraps(f)
    def apply(t: Term) -> T:
        if doing_fixpoint:
            assert isinstance(t, Var)
            return rewriter.fix_cache[(f, t)]
        if isinstance(t, Var):
            with fixpointing():
                return kildall(t)
        else:
            return f(t)
    return apply


fixpoint = lambda bot: lambda f: _fixpoint(f, bot)
