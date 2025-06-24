from runllm.constrained_decoding import RealizabilityChecker
from tests.utils import reset
from experiments.egraph.let import *

egraph_expression_grammar_checker = RealizabilityChecker(
    lambda x: x,
    E(),
    lexer_spec,
)

@reset
def test_egraph_expression_grammar():
    assert egraph_expression_grammar_checker.realizable("")
    assert egraph_expression_grammar_checker.realizable("x")
    assert egraph_expression_grammar_checker.realizable("42")
    assert egraph_expression_grammar_checker.realizable("(x)")
    
    assert egraph_expression_grammar_checker.realizable("x + y")
    assert egraph_expression_grammar_checker.realizable("x * y")
    assert egraph_expression_grammar_checker.realizable("x + y * z")
    assert egraph_expression_grammar_checker.realizable("(x + y) * z")

    assert egraph_expression_grammar_checker.realizable("f x")
    assert egraph_expression_grammar_checker.realizable("f x y")
    assert egraph_expression_grammar_checker.realizable("f x + g y")

    assert egraph_expression_grammar_checker.realizable("let x = 1 in x")
    assert egraph_expression_grammar_checker.realizable("let x = f y in x * z")
    assert egraph_expression_grammar_checker.realizable("let x = 1 in let y = 2 in x + y")
    
    assert egraph_expression_grammar_checker.realizable("x +")
    assert egraph_expression_grammar_checker.realizable("let")
    assert egraph_expression_grammar_checker.realizable("let x =")
    assert egraph_expression_grammar_checker.realizable("let x = 1 in")
    assert egraph_expression_grammar_checker.realizable("(x + y")
    
    assert not egraph_expression_grammar_checker.realizable("x -")
    assert not egraph_expression_grammar_checker.realizable("+ x")
    assert not egraph_expression_grammar_checker.realizable("let =")
    assert not egraph_expression_grammar_checker.realizable(")")
    assert not egraph_expression_grammar_checker.realizable("()")
