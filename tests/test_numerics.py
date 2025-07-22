from .utils import *
from core.rewrite import *
from core.grammar import *
from core.lexing.token import Token
import regex


# Note: this file is only used to test tree grammar code,
# so the functions do not handle incomplete tokens.


def int_token(i):
    return Token("Int", regex.compile(r"\d+"), prefix=str(i), is_complete=True)


ONE = int_token(1)
TWO = int_token(2)


@rewrite
def ones():
    return Union.of(ONE, Application.of("Add", ONE, ones()))


@rewrite
def twos():
    return Union.of(TWO, Application.of("Add", TWO, twos()))


@rewrite
def constant1():
    return ONE


@rewrite
def evens(t: TreeGrammar):
    match t:
        case EmptySet():
            return EmptySet()
        case Token(prefix=prefix, is_complete=True):
            return t if int(prefix) % 2 == 0 else EmptySet()
        case Application(PLUS, (left, right)):
            return Union.of(
                Application.of(PLUS, evens(left), evens(right)),
                Application.of(PLUS, odds(left), odds(right)),
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
        case Token(prefix=prefix, is_complete=True):
            return t if int(prefix) % 2 == 1 else EmptySet()
        case Application(PLUS, (left, right)):
            return Union.of(
                Application.of(PLUS, evens(left), odds(right)),
                Application.of(PLUS, odds(left), evens(right)),
            )
        case Union(children):
            return Union.of(odds(c) for c in children)
        case _:
            raise ValueError


@reset
def test_even_odd():
    assert is_nonempty(constant1())
    assert is_empty(odds(TWO))
    assert is_nonempty(evens(ones()))
    assert is_empty(odds(odds(evens(ones()))))
    assert is_nonempty(evens(twos()))
    assert is_empty(odds(twos()))
    assert is_empty(evens(Application.of("Add", ONE, evens(twos()))))


@rewrite
def less_than(n: int, t: TreeGrammar):
    match t:
        case EmptySet():
            return EmptySet()
        case Token(prefix=prefix, is_complete=True):
            return t if int(prefix) < n else EmptySet()
        case Application(PLUS, (left, right)):
            return Union.of(
                Application.of(PLUS, less_than(j, left), less_than(n - j, right))
                for j in range(n)
            )
        case Union(children):
            return Union.of(less_than(n, c) for c in children)
        case _:
            raise ValueError


@reset
def test_less_than():
    assert is_nonempty(less_than(2, ones()))
    assert is_empty(less_than(-1, ones()))
    assert is_empty(less_than(0, ones()))
    assert is_empty(less_than(1, twos()))
    assert is_empty(less_than(48, int_token(48)))
    assert is_nonempty(less_than(48, int_token(47)))
