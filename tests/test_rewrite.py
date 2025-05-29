from lexing.leaves import IntLeaf, StringLeaf
from .utils import *
from core.rewrite import *
from core.grammar import *


ONE = IntLeaf(1)
TWO = IntLeaf(2)
PLUS = StringLeaf("+")


@rewrite
def E():
    return Union.of(
        Constant(ONE),
        Application.of(PLUS, (Constant(ONE), E()))
    )


@rewrite
def X():
    return Union.of(X(), X())


@rewrite
def A():
    return Union.of(A(), B())


@rewrite
def B():
    return Union.of(A())


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
        assert dependencies_isomorphic_to(DiGraph({"A": [], "B": []}))

    @reset
    def test_X(self):
        X()
        assert len(rewriter.equations) == 1
        assert dependencies_isomorphic_to(DiGraph({"empty": []}))


class TestFixpoint:
    @reset
    def test_nonempty_basic(self):
        assert is_empty(EmptySet())
        assert is_empty(Union.of(EmptySet(), EmptySet()))
        assert is_nonempty(Constant(ONE))
        assert is_nonempty(Application.of(PLUS, (Constant(ONE), Constant(2))))
        assert is_nonempty(Union.of(Constant(ONE), EmptySet()))
        assert is_nonempty(Union.of(EmptySet(), Constant(ONE)))
        assert is_nonempty(Union.of(Constant(ONE), Constant(2)))

    @reset
    def test_nonempty(self):
        assert is_nonempty(E())
        assert is_empty(X())

    @reset
    def test_nonempty_mutual(self):
        assert is_empty(A())
        assert is_empty(B())
