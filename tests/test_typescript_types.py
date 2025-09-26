from tests.utils import reset
from experiments.typescript.types import *


@reset
def test_types_contains():
    assert contains(NUMBERTYPE, NUMBERTYPE)
    assert contains(NUMBERTYPE, EmptyType())
    assert contains(TopType(), NUMBERTYPE)
    assert contains(ProdType.of(NUMBERTYPE, NUMBERTYPE),
                    ProdType.of(NUMBERTYPE, NUMBERTYPE))
    assert contains(ProdType.of(NUMBERTYPE, TopType()),
                    ProdType.of(NUMBERTYPE, NUMBERTYPE))
    assert contains(ProdType.of(NUMBERTYPE, BOOLEANTYPE),
                    ProdType.of(NUMBERTYPE, EmptyType()))
    assert contains(FuncType.of(ProdType.of(NUMBERTYPE, NUMBERTYPE),
                                BOOLEANTYPE),
                    FuncType.of(ProdType.of(NUMBERTYPE, NUMBERTYPE),
                                BOOLEANTYPE))
    assert contains(FuncType.of(ProdType.of(TopType(), NUMBERTYPE),
                                TopType()),
                    FuncType.of(ProdType.of(NUMBERTYPE, NUMBERTYPE),
                                BOOLEANTYPE))
    assert not contains(STRINGTYPE, NUMBERTYPE)
    assert not contains(EmptyType(), NUMBERTYPE)
    assert not contains(NUMBERTYPE, TopType())
    assert not contains(ProdType.of(STRINGTYPE, NUMBERTYPE),
                        ProdType.of(NUMBERTYPE, NUMBERTYPE))
    assert not contains(ProdType.of(EmptyType(), NUMBERTYPE),
                        ProdType.of(NUMBERTYPE, NUMBERTYPE))
    assert not contains(ProdType.of(TopType(), TopType()),
                        FuncType.of(ProdType.of(NUMBERTYPE, NUMBERTYPE),
                                    BOOLEANTYPE))
    assert not contains(ProdType.of(NUMBERTYPE),
                        ProdType.of(TopType()))
    assert not contains(FuncType.of(ProdType.of(), NumberType()),
                        FuncType.of(ProdType.of(), BooleanType()))


@reset
def test_types_contains_extensible():
    # Type 1 extensible, Type 2 not.
    assert contains(ProdType.of(NUMBERTYPE, extensible=True),
                    ProdType.of(NUMBERTYPE, NUMBERTYPE))
    assert not contains(ProdType.of(NUMBERTYPE, BOOLEANTYPE, extensible=True),
                        ProdType.of(NUMBERTYPE, NUMBERTYPE))
    assert contains(ProdType.of(NUMBERTYPE, NUMBERTYPE, extensible=True),
                    ProdType.of(NUMBERTYPE, NUMBERTYPE))
    assert not contains(ProdType.of(NUMBERTYPE, extensible=True),
                        ProdType.of())
    # Type1 and Type2 extensible
    assert contains(ProdType.of(NUMBERTYPE, extensible=True),
                    ProdType.of(NUMBERTYPE, extensible=True))
    assert contains(ProdType.of(TopType(), extensible=True),
                    ProdType.of(NUMBERTYPE, extensible=True))
    assert not contains(ProdType.of(NUMBERTYPE, BOOLEANTYPE, extensible=True),
                        ProdType.of(NUMBERTYPE, NUMBERTYPE, extensible=True))
    assert contains(ProdType.of(NUMBERTYPE, extensible=True),
                    ProdType.of(NUMBERTYPE, NUMBERTYPE, extensible=True))
    assert not contains(ProdType.of(NUMBERTYPE, extensible=True),
                        ProdType.of(BOOLEANTYPE, NUMBERTYPE, extensible=True))
    assert not contains(ProdType.of(NUMBERTYPE, NUMBERTYPE, extensible=True),
                        ProdType.of(NUMBERTYPE, extensible=True))
    assert not contains(ProdType.of(NUMBERTYPE, NUMBERTYPE, extensible=True),
                        ProdType.of(BOOLEANTYPE, extensible=True))
    # Type1 not extensible, Type2 extensible
    assert not contains(ProdType.of(NUMBERTYPE, extensible=False),
                        ProdType.of(NUMBERTYPE, extensible=True))
    assert not contains(ProdType.of(TopType(), extensible=False),
                        ProdType.of(NUMBERTYPE, extensible=True))
    assert not contains(ProdType.of(NUMBERTYPE, BOOLEANTYPE, extensible=False),
                        ProdType.of(NUMBERTYPE, NUMBERTYPE, extensible=True))
    assert not contains(ProdType.of(NUMBERTYPE, extensible=False),
                        ProdType.of(NUMBERTYPE, NUMBERTYPE, extensible=True))
    assert not contains(ProdType.of(NUMBERTYPE, extensible=False),
                        ProdType.of(BOOLEANTYPE, NUMBERTYPE, extensible=True))
    assert not contains(ProdType.of(NUMBERTYPE, NUMBERTYPE, extensible=False),
                        ProdType.of(NUMBERTYPE, extensible=True))
    assert not contains(ProdType.of(NUMBERTYPE, NUMBERTYPE, extensible=False),
                        ProdType.of(BOOLEANTYPE, extensible=True))
    # Type1 and Type2 not extensible
    assert not contains(ProdType.of(extensible=False),
                        ProdType.of(NUMBERTYPE, BOOLEANTYPE, extensible=False),)
    assert not contains(ProdType.of(extensible=False),
                        ProdType.of(NUMBERTYPE, BOOLEANTYPE, extensible=False),)
    assert not contains(ProdType.of(NUMBERTYPE, extensible=False),
                        ProdType.of(extensible=False))
    assert not contains(ProdType.of(NUMBERTYPE, BOOLEANTYPE, extensible=False),
                        ProdType.of(extensible=False))
    # Small tests in functions.
    assert contains(FuncType.of(ProdType.of(NUMBERTYPE, extensible=True),
                                BOOLEANTYPE),
                    FuncType.of(ProdType.of(NUMBERTYPE, NUMBERTYPE),
                                BOOLEANTYPE))
    assert not contains(FuncType.of(ProdType.of(NUMBERTYPE, extensible=False),
                                    BOOLEANTYPE),
                        FuncType.of(ProdType.of(NUMBERTYPE, NUMBERTYPE),
                                    BOOLEANTYPE))


@reset
def test_prodtype_reduces():
    assert contains(ProdType.of(NUMBERTYPE), NUMBERTYPE)
    assert contains(ProdType.of(NUMBERTYPE, extensible=True), NUMBERTYPE)
    assert contains(ProdType.of(extensible=True), NUMBERTYPE)
    assert contains(NUMBERTYPE, ProdType.of(NUMBERTYPE))
    assert not contains(NUMBERTYPE, ProdType.of(NUMBERTYPE, extensible=True))


@reset
def test_types_depth():
    assert isinstance(NUMBERTYPE.condense(1), NumberType)
    assert isinstance(NUMBERTYPE.condense(0), TopType)
    assert isinstance(STRINGTYPE.condense(1), StringType)
    assert isinstance(STRINGTYPE.condense(0), TopType)
    assert isinstance(BOOLEANTYPE.condense(1), BooleanType)
    assert isinstance(BOOLEANTYPE.condense(0), TopType)
    assert isinstance(TopType().condense(1), TopType)
    assert isinstance(TopType().condense(0), TopType)
    assert isinstance(EmptyType().condense(0), EmptyType)
    assert isinstance(ProdType.of(NUMBERTYPE, NUMBERTYPE
                                  ).condense(0),
                      TopType)
    assert (ProdType.of(NUMBERTYPE, NUMBERTYPE).condense(1)
            == ProdType.of(TopType(), TopType()))
    assert (ProdType.of(NUMBERTYPE, NUMBERTYPE).condense(2)
            == ProdType.of(NUMBERTYPE, NUMBERTYPE))
    assert (ProdType.of(ProdType.of(NUMBERTYPE, NUMBERTYPE),
                        NUMBERTYPE).condense(2)
            == ProdType.of(ProdType.of(TopType(), TopType()), NUMBERTYPE))
    assert isinstance(FuncType.of(ProdType.of(), NUMBERTYPE).condense(0),
                      TopType)
    assert isinstance(FuncType.of(ProdType.of(NUMBERTYPE, NUMBERTYPE),
                                  NUMBERTYPE).condense(0),
                      TopType)
    assert (FuncType.of(ProdType.of(NUMBERTYPE, NUMBERTYPE), NUMBERTYPE
                        ).condense(1)
            == FuncType.of(ProdType.of(TopType(), TopType()), TopType()))
    assert (FuncType.of(ProdType.of(NUMBERTYPE, NUMBERTYPE), NUMBERTYPE
                        ).condense(2)
            == FuncType.of(ProdType.of(NUMBERTYPE, NUMBERTYPE), NUMBERTYPE))
    assert (
        FuncType.of(
            ProdType.of(FuncType.of(ProdType.of(), NUMBERTYPE),
                        NUMBERTYPE),
            FuncType.of(ProdType.of(), BOOLEANTYPE)
        ).condense(3)
        == FuncType.of(
            ProdType.of(FuncType.of(ProdType.of(), NUMBERTYPE),
                        NUMBERTYPE),
            FuncType.of(ProdType.of(), BOOLEANTYPE)
        )
    )
    assert (
        FuncType.of(
            ProdType.of(FuncType.of(ProdType.of(), NUMBERTYPE),
                        NUMBERTYPE),
            FuncType.of(ProdType.of(), BOOLEANTYPE)
        ).condense(2)
        == FuncType.of(
            ProdType.of(FuncType.of(ProdType.of(), TopType()),
                        NUMBERTYPE),
            FuncType.of(ProdType.of(), TopType())
        )
    )
    assert (
        FuncType.of(
            ProdType.of(FuncType.of(ProdType.of(), NUMBERTYPE),
                        NUMBERTYPE),
            FuncType.of(ProdType.of(), BOOLEANTYPE)
        ).condense(1)
        == FuncType.of(
            ProdType.of(TopType(), TopType()),
            TopType()
        )
    )
