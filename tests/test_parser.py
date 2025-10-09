from core.parser import *
from .utils import *
from core.lexing.token import Token
import regex


ZERO = Token("ZERO", regex.compile(r"0"), prefix="0", is_complete=True)
ONE = Token("ONE", regex.compile(r"1"), prefix="1", is_complete=True)
PLUS = Token("Plus", regex.compile(r"\+"), prefix="+", is_complete=True)
MINUS = Token("Minus", regex.compile(r"\-"), prefix="-", is_complete=True)


@rewrite
def parse_E():
    return Choice.of(
        ConstantParser(ONE),
        Concatenation.of(
            ConstantParser(ONE),
            ConstantParser(PLUS),
            parse_E(),
            rearrange=Rearrangement("+", (0, 2)),
        ),
    )


@reset
def test_parser():
    assert parser_nonempty(parse_E())


@reset
def test_derivative():
    assert parser_nonempty(D(ONE, parse_E()))
    assert parser_empty(D(ZERO, parse_E()))
    assert parser_nonempty(D(PLUS, D(ONE, parse_E())))
    assert parser_empty(D(MINUS, D(ONE, parse_E())))
