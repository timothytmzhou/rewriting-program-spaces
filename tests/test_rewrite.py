from .utils import *
from core.rewrite import *
from core.grammar import *
from lexing.token import Token
import regex


ZERO = Token("ZERO", regex.compile(r"0"), prefix="0", is_complete=True)
ONE = Token("ONE", regex.compile(r"1"), prefix="1", is_complete=True)


@rewrite
def E():
    return Union.of(ONE, Application.of("Add", (ONE, E())))


@rewrite
def A():
    return Union.of(A(), B())


@rewrite
def B():
    return A()


class TestEquationGeneration:
    @reset
    def test_E(self):
        E()
        assert len(rewriter.equations) == 1
        assert dependencies_isomorphic_to(DiGraph([("E", "E")]))

    @reset
    def test_A(self):
        A()
        assert len(rewriter.equations) == 2
        assert dependencies_isomorphic_to(DiGraph([("A", "B")]))


class TestFixpoint:
    @reset
    def test_nonempty_basic(self):
        assert is_empty(EmptySet())
        assert is_empty(Union.of(EmptySet(), EmptySet()))
        assert is_nonempty(ONE)
        assert is_nonempty(Application.of("Add", (ONE, ZERO)))
        assert is_nonempty(Union.of(ONE, EmptySet()))
        assert is_nonempty(Union.of(EmptySet(), ONE))
        assert is_nonempty(Union.of(ONE, ZERO))

    @reset
    def test_nonempty(self):
        assert is_nonempty(E())

    @reset
    def test_nonempty_mutual(self):
        assert is_empty(A())
        assert is_empty(B())
