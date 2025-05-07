from dataclasses import dataclass
from networkx import DiGraph
from functools import partial, wraps
from typing import Any, TypeVar, Callable, Hashable, Optional

T = TypeVar("T")


class Term:
    pass


@dataclass(frozen=True)
class Var(Term):
    name: str


@dataclass
class Thunk[T]:
    f: Callable[..., T]
    args: tuple[Hashable]

    def __call__(self):
        return self.f(*self.args)

    def __repr__(self):
        return f"Thunk({self.f.__name__}, {str(self.args)})"

    def __hash__(self):
        return hash((self.f, self.args))


type ThunkableTerm = Term | Thunk[Term]


class FixpointSolver:
    f: Callable[[Term], Any]
    bot: Callable[[], Any]
    worklist: list[Term]
    dependencies: DiGraph
    cache: dict[Term, Any]
    current_term: Term

    def __init__(self, f, bot):
        self.f = f
        self.bot = bot
        self.worklist = []
        self.dependencies = DiGraph()
        self.cache = {}
        self.current_term = None

    def visit_subterm(self, t: Term):
        if t in self.cache:
            return self.cache[t]
        self.worklist.append(t)
        self.cache[t] = self.bot()
        if self.current_term is not None:
            self.dependencies.add_edge(t, self.current_term)
        return self.cache[t]

    def compute_fixpoint(self, start: Term):
        self.visit_subterm(start)
        while self.worklist:
            current = self.worklist.pop()
            self.current_term = current
            assert current in self.cache
            old = self.cache[current]
            result = self.f(current)
            self.cache[current] = result
            if old != result and current in self.dependencies:
                for parent in self.dependencies.successors(current):
                    self.worklist.append(parent)
        return self.cache[start]


class RewriteSystem:
    env: dict[Var, ThunkableTerm]
    id: int
    call_names: dict[tuple[Callable, tuple], Var]
    solver: Optional[FixpointSolver]

    def __init__(self):
        self.env = {}
        self.id = 0
        self.call_names = {}
        self.solver = None

    def fresh_var(self, base="") -> Var:
        name = f"{base}@{self.id}"
        self.id += 1
        var = Var(name)
        return var

    def expand_term(self, t: Term) -> Term:
        if isinstance(t, Var):
            assert t in self.env
            value = self.env[t]
            expanded: Term
            if isinstance(value, Thunk):
                expanded = value()
                self.env[t] = expanded
            else:
                expanded = value
            assert not isinstance(
                expanded, Var), "This is likely due to a single variable definition, which is not allowed."
            return expanded
        return t

    def expand_args(self, args: tuple) -> tuple:
        return tuple(
            self.expand_term(arg) if isinstance(arg, Term) else arg
            for arg in args
        )

    def rewrite(self, f):
        """
        Decorator to convert a function into a rewrite rule.
        The function should return a Term and only have hashable, non-keyword arguments.
        Calling the wrapped function will return a Var that represents the result of the rewrite.
        """
        @wraps(f)
        def var_for_call(*args) -> Var:
            expand_f = lambda *unexpanded: f(*self.expand_args(unexpanded))
            thunk = Thunk(expand_f, args)
            if (f, args) in self.call_names:
                return self.call_names[(f, args)]
            else:
                var = self.fresh_var(f"{f.__name__}({', '.join(map(str, args))})")
                self.call_names[(f, args)] = var
                self.env[var] = thunk
                return var
        return var_for_call

    def fix(self, bot, f):
        """
        Transforms a function into one which will perform a fixpoint computation.
        The function should take a Term and return a result.
        """
        @wraps(f)
        def wrapped(t):
            expanded = self.expand_term(t)
            if self.solver is None:
                self.solver = FixpointSolver(f, bot)
                result = self.solver.compute_fixpoint(expanded)
                self.solver = None
                return result
            else:
                return self.solver.visit_subterm(expanded)
        return wrapped


rewriter = RewriteSystem()
rewrite = rewriter.rewrite
fixpoint = lambda bot: partial(rewriter.fix, bot)
