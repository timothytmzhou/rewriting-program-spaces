from core.rewrite import *
from core.grammar import *


@rewrite
def E():
    return Union(
        Constant(1),
        Application("+", (Constant(1), E()))
    )


@rewrite
def X():
    return Union(X(), X())


@rewrite
def A():
    return Union(A(), B())


@rewrite
def B():
    return Union(A())


def test_nonempty_basic():
    assert not is_nonempty(EmptySet())
    assert not is_nonempty(Union(EmptySet(), EmptySet()))
    assert is_nonempty(Constant(1))
    assert is_nonempty(Application("+", (Constant(1), Constant(2))))
    assert is_nonempty(Union(Constant(1), EmptySet()))
    assert is_nonempty(Union(EmptySet(), Constant(1)))
    assert is_nonempty(Union(Constant(1), Constant(2)))


def test_nonempty():
    assert is_nonempty(E())
    assert not is_nonempty(X())


def test_nonempty_mutual():
    assert not is_nonempty(A())
    assert not is_nonempty(B())
