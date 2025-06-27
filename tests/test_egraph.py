from runllm.constrained_decoding import RealizabilityChecker
from tests.utils import reset
from experiments.egraph.let import *
from experiments.egraph.egraph import *


eqsat_basic = """(datatype Math
(Num i64)
(Var String)
(Add Math Math)
(Mul Math Math))


(rewrite (Add a b)
        (Add b a))
(rewrite (Mul a (Add b c))
        (Add (Mul a b) (Mul a c)))
(rewrite (Add (Num a) (Num b))
        (Num (+ a b)))
(rewrite (Mul (Num a) (Num b))
        (Num (* a b)))
"""

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
    assert egraph_expression_grammar_checker.realizable(
        "let x = 1 in let y = 2 in x + y")

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


source = """
(let six (Num 6))
(let times (Mul (Num 3) (Num 2)))
(let add (Add (Num 3) (Num 3)))
(let var (Var "x"))
(rewrite (Var "x") (Num 6))
(run 100)
"""
source = eqsat_basic + source
egraph = egraph_from_egglog(source, "six", "Math")

@reset
def test_static_egraph():
    checker = RealizabilityChecker(
        in_egraph(egraph),
        E(),
        lexer_spec,
    )
    assert checker.realizable("")
    assert checker.realizable("6")
    assert checker.realizable("3 * 2")
    assert checker.realizable("3 *")
    assert checker.realizable("3 + ")
    assert checker.realizable("x")
    # egraph doesn't have certain constants in it, so these are not realizable
    assert not checker.realizable("2 +")
    assert not checker.realizable("6 *")
    assert not checker.realizable("x +")

@reset
def test_dynamic_egraph():
    checker = RealizabilityChecker(
        lambda t: equiv(egraph, t),
        E(),
        lexer_spec,
    )
    assert checker.realizable("let y = 3 in 3")
    assert checker.realizable("let y = 6 in y")
    assert checker.realizable("let z = 3 * 2 in z")
    assert checker.realizable("let u = 3 in let v = 2 in u * v")
    assert checker.realizable("let")
    assert checker.realizable("")
    assert checker.realizable("6")
    assert checker.realizable("3 * 2")
    assert checker.realizable("3 *")
    assert checker.realizable("3 + ")
    assert checker.realizable("x")
    # egraph doesn't have certain constants in it, so these are not realizable
    assert not checker.realizable("let z = 3 * 2 in z +")
    assert not checker.realizable("2 +")
    assert not checker.realizable("6 *")
    assert not checker.realizable("x +")
