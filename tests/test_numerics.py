from .utils import *
from core.rewrite import *
from core.grammar import *


@rewrite
def even_val(t: TreeGrammar):
    match t:
        case EmptySet():
            return EmptySet()
        case Constant(c):
            if c % 2 == 0:
                return Constant(c)
            else:
                return EmptySet()
        case Application("+", children):
            return Union.of(
                Application.of("+", even_val(children[0]), even_val(children[1])),
                Application.of("+", odd_val(children[0]), odd_val(children[1]))
            )
        case Union(children):
            return Union.of(
                *[even_val(c) for c in children]
            )
        case _:
            raise TypeError(f"Unexpected type: {type(t)}")


@rewrite
def odd_val(t: TreeGrammar):
    match t:
        case EmptySet():
            return EmptySet()
        case Constant(c):
            if c % 2 == 1:
                return Constant(c)
            else:
                return EmptySet()
        case Application("+", children):
            return Union.of(
                Application.of("+", even_val(children[0]), odd_val(children[1])),
                Application.of("+", odd_val(children[0]), even_val(children[1]))
            )
        case Union(children):
            return Union.of(
                *[odd_val(c) for c in children]
            )
        case _:
            raise TypeError(f"Unexpected type: {type(t)}")


@rewrite
def less_than(n: int, t: TreeGrammar):
    match t:
        case EmptySet():
            return EmptySet()
        case Constant(c):
            if c < n:
                return Constant(c)
            else:
                return EmptySet()
        case Application("+", children):
            return Union.of(
                Application.of("+", less_than(j, children[0]), less_than(n - j, children[1]))
                for j in range(n)
            )
        case Union(children):
            return Union.of(
                *[less_than(n, c) for c in children]
            )
        case _:
            raise TypeError(f"Unexpected type: {type(t)}")


@rewrite
def E():
    return Union.of(
        Constant(1),
        Application.of("+", (Constant(1), E()))
    )

# E ::=  1 | 1 + E

@rewrite
def Twos():
    return Union.of(
        Constant(2),
        Application.of("+", (Constant(2), Twos()))
    )


@rewrite
def cons1():
    return Constant(1)


class TestNumerics:
    @reset
    def test_even_val(self):
        assert is_nonempty(cons1())
        assert not is_nonempty(odd_val(Constant(2)))
        assert is_nonempty(even_val(E()))
        assert not is_nonempty(odd_val(odd_val(even_val(E()))))
        assert is_nonempty(even_val(Twos()))
        assert not is_nonempty(Application.of("+", [Constant(1), even_val(Twos())]))
        assert not is_nonempty(odd_val(Twos()))

    @reset
    def test_less_than(self):
        assert is_nonempty(less_than(2, E()))
        assert not is_nonempty(less_than(-1, E()))
        assert not is_nonempty(less_than(0, E()))
        assert not is_nonempty(less_than(1, Twos()))
        assert not is_nonempty(less_than(48, Constant(49)))
        assert is_nonempty(less_than(48, Constant(47)))
