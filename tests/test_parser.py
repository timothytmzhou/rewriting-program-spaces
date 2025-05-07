from core.parser import *

@rewrite
def parse_E():
    return Choice.of(
        ConstantParser(1),
        Concatenation.of("+", ConstantParser(1), ConstantParser("+"), parse_E(), rearrange=(0, 2))
    )

@rewrite
def parses_nothing():
    return Choice.of(EmptyParser(), parses_nothing())

def test_parser():
    assert is_nonempty(image(parse_E()))
    assert not is_nonempty(image(parses_nothing()))
    
def test_derivative():
    assert is_nonempty(image(D(1, parse_E())))
    assert not is_nonempty(image(D(0, parse_E())))    
    assert is_nonempty(image(D("+", D(1, parse_E()))))