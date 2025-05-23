from .utils import *
from core.rewrite import *
from core.grammar import *


@rewrite
def ones():
    return Union.of(
        Constant(1),
        Application.of("+", (Constant(1), ones()))
    )


@rewrite
def twos():
    return Union.of(
        Constant(2),
        Application.of("+", (Constant(2), twos()))
    )


@rewrite
def constant1():
    return Constant(1)


@rewrite
def evens(t: TreeGrammar):
    match t:
        case EmptySet():
            return EmptySet()
        case Constant(c):
            return t if c % 2 == 0 else EmptySet()
        case Application("+", (left, right)):
            return Union.of(
                Application.of("+", evens(left), evens(right)),
                Application.of("+", odds(left), odds(right))
            )
        case Union(children):
            return Union.of(evens(c) for c in children)
        case _:
            raise ValueError


@rewrite
def odds(t: TreeGrammar):
    match t:
        case EmptySet():
            return EmptySet()
        case Constant(c):
            return t if c % 2 == 1 else EmptySet()
        case Application("+", (left, right)):
            return Union.of(
                Application.of("+", evens(left), odds(right)),
                Application.of("+", odds(left), evens(right))
            )
        case Union(children):
            return Union.of(odds(c) for c in children)
        case _:
            raise ValueError


@reset
def test_even_odd():
    assert is_nonempty(constant1())
    assert not is_nonempty(odds(Constant(2)))
    assert is_nonempty(evens(ones()))
    assert not is_nonempty(odds(odds(evens(ones()))))
    assert is_nonempty(evens(twos()))
    assert not is_nonempty(odds(twos()))


@rewrite
def less_than(n: int, t: TreeGrammar):
    match t:
        case EmptySet():
            return EmptySet()
        case Constant(c):
            return t if c < n else EmptySet()
        case Application("+", (left, right)):
            return Union.of(
                Application.of("+", less_than(j, left), less_than(n - j, right))
                for j in range(n)
            )
        case Union(children):
            return Union.of(less_than(n, c) for c in children)
        case _:
            raise ValueError


@reset
def test_less_than():
    assert is_nonempty(less_than(2, ones()))
    assert not is_nonempty(less_than(-1, ones()))
    assert not is_nonempty(less_than(0, ones()))
    assert not is_nonempty(less_than(1, twos()))
    assert not is_nonempty(less_than(48, Constant(49)))
    assert is_nonempty(less_than(48, Constant(47)))
