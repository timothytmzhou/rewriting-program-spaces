from core.parser import *
from .utils import *


@rewrite
def parse_E():
    return Choice.of(
        ConstantParser(1),
        Concatenation.of(
            "+",
            ConstantParser(1),
            ConstantParser("+"),
            parse_E(),
            rearrange=(0, 2)
        )
    )


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
