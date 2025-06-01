from core.parser import *
from lexing.leaves import IntLeaf, StringLeaf
from .utils import *


@rewrite
def parse_E():
    return Choice.of(
        ConstantParser(IntLeaf(1)),
        Concatenation.of(
            ConstantParser(IntLeaf(1)),
            ConstantParser(StringLeaf("+")),
            parse_E(),
            rearrange=Rearrangement("+", (0, 2))
        )
    )


@rewrite
def parse_C():
    return parse_C()


@rewrite
def parses_nothing():
    return Choice.of(EmptyParser(), parses_nothing())


@reset
def test_parser():
    assert parser_nonempty(parse_E())
    assert parser_empty(parses_nothing())


@reset
def test_derivative():
    assert parser_nonempty(D(1, parse_E()))
    assert parser_empty(D(0, parse_E()))
    assert parser_nonempty(D("+", D(1, parse_E())))
    assert parser_empty(D("-", D(1, parse_E())))


@reset
def test_self_loop_app():
    assert parser_nonempty(D(1, parse_C()))
