from __future__ import annotations
from matplotlib import pyplot as plt
import networkx as nx
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Iterable, TypeVar
from networkx import DiGraph
from contextlib import contextmanager
from collections import deque
from .utils import replace_adjacency_list


T = TypeVar('T')


class Term:
    def subterms(self) -> Iterable[Term]:
        return set()

    def _var_descendents(self) -> Iterable[Var]:
        for subterm in self.subterms():
            if isinstance(subterm, Term):
                yield from subterm._var_descendents()
            elif isinstance(subterm, Var):
                yield subterm

    def compact(self):
        return self


vHashMap: dict[tuple[Callable, tuple], int] = dict()
vctr = 0


@dataclass(frozen=True)
class Var:  # should not subclass Term here since we want mypy to distinguish
    f: Callable
    args: tuple
    hashval: int = -1

    def __post_init__(self):
        global vctr
        object.__setattr__(self, 'hashval', vHashMap.get((self.f, self.args)))
        if self.hashval is None:
            vctr += 1
            vHashMap[(self.f, self.args)] = vctr
            object.__setattr__(self, 'hashval', vctr)

    def expand(self) -> Term:
        if self in rewriter.equations:
            return rewriter.equations[self]
        expanded_args = [
            arg.expand() if isinstance(arg, Var) else arg
            for arg in self.args
        ]
        assert not any(isinstance(arg, Var)
                       for arg in expanded_args), "rewrite with non-value RHS detected"
        term = self.f(*expanded_args)
        assert isinstance(term, Term)
        rewriter.equations[self] = term
        rewriter.dependencies.add_node(self)
        var_descendents = list(term._var_descendents())
        rewriter.dependencies.add_edges_from(
            (self, dep) for dep in var_descendents
        )
        rewriter.worklist.extend(var_descendents)
        return term

    def __str__(self):
        return f"{self.f.__name__}({', '.join(str(arg) for arg in self.args)})"

    def __hash__(self):
        return self.hashval


class RewriteSystem:
    equations: dict[Var, Term]
    fix_cache: dict[tuple[Callable, Var], Any]
    dependencies: DiGraph
    worklist: deque[Var]

    def __init__(self):
        self.dependencies = DiGraph()
        self.equations = {}
        self.fix_cache = {}
        self.worklist = deque()

    def clear(self):
        self.dependencies.clear()
        self.equations.clear()
        self.fix_cache.clear()
        self.worklist.clear()

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

    def plot(self):
        """Plots the dependency graph of the rewrite system."""
        pos = nx.spring_layout(self.dependencies)
        nx.draw(self.dependencies, pos, with_labels=True, arrows=True)
        labels = {var: str(var) for var, term in self.equations.items()}
        nx.draw_networkx_labels(self.dependencies, pos, labels=labels)
        plt.show()


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
    def start_rewrite(start_var: Var) -> Var:
        rewriter.worklist.append(start_var)
        to_compact = []
        while rewriter.worklist:
            current = rewriter.worklist.popleft()
            if current in rewriter.equations:
                continue
            term = current.expand()
            to_compact.append(current)

        # simplify the equations
        for var in to_compact:
            term = rewriter.equations[var]
            assert isinstance(term, Term)
            compacted = term.compact()
            rewriter.equations[var] = compacted
            replace_adjacency_list(rewriter.dependencies, var,
                                   compacted._var_descendents())
        return start_var

    @wraps(f)
    def apply(*args) -> Var:
        # TODO: could cache less
        var = Var(f, args)
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


fixpoint = lambda bot: lambda f: _fixpoint(f, bot)
