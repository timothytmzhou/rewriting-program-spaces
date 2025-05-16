from dataclasses import dataclass
from functools import wraps
from typing import Callable, Optional
from networkx import DiGraph
from contextlib import contextmanager
from collections import deque


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


class RewriteSystem:
    equations: dict[Var, Term]
    dependencies: DiGraph
    worklist: deque[Var]

    def __init__(self):
        self.dependencies = DiGraph()
        self.equations = {}
        self.worklist = deque()

    def clear(self):
        self.dependencies.clear()
        self.equations.clear()
        self.worklist.clear()


rewriter = RewriteSystem()  # not super thread safe
is_rewriting: bool = False
origin: Optional[Var] = None


@contextmanager
def rewriting():
    global is_rewriting
    try:
        is_rewriting = True
        yield
    finally:
        is_rewriting = False


def set_origin(new_origin: Var):
    global origin
    origin = new_origin


def rewrite(f):
    """
    Rewrite a (infinitely recursive) function into a capsule of equations.
    """
    def start_rewrite(start: Var) -> Term:
        assert not rewriter.worklist
        rewriter.worklist.append(start)
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
        return rewriter.equations[start]

    def visit(var) -> Var:
        rewriter.worklist.append(var)
        rewriter.dependencies.add_edge(var, origin)
        return var

    @wraps(f)
    def apply(*args) -> Var | Term:
        var = Var(f, args)
        if is_rewriting:
            return visit(var)
        with rewriting():
            return start_rewrite(var)
    return apply
