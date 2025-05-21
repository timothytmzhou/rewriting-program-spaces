from .utils import *
from core.rewrite import *
from core.grammar import *


@rewrite
def E():
    return Union.of(
        Constant(1),
        Application.of("+", (Constant(1), E()))
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
        assert dependencies_isomorphic_to([("E", "E")])

    @reset
    def test_A(self):
        A()
        assert len(rewriter.equations) == 2
        assert dependencies_isomorphic_to([("A", "B"), ("B", "A"), ("A", "A")])

    @reset
    def test_X(self):
        X()
        assert len(rewriter.equations) == 1
        assert dependencies_isomorphic_to([("X", "X")])


class TestFixpoint:
    @reset
    def test_nonempty_basic(self):
        assert not is_nonempty(EmptySet())
        assert not is_nonempty(Union.of(EmptySet(), EmptySet()))
        assert is_nonempty(Constant(1))
        assert is_nonempty(Application.of("+", (Constant(1), Constant(2))))
        assert is_nonempty(Union.of(Constant(1), EmptySet()))
        assert is_nonempty(Union.of(EmptySet(), Constant(1)))
        assert is_nonempty(Union.of(Constant(1), Constant(2)))

    @reset
    def test_nonempty(self):
        assert is_nonempty(E())
        assert not is_nonempty(X())

    @reset
    def test_nonempty_mutual(self):
        assert not is_nonempty(A())
        assert not is_nonempty(B())
