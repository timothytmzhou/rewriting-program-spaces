from runllm.constrained_decoding import RealizabilityChecker
from tests.utils import reset
from experiments.egraph.let import *
from experiments.egraph.egraph import *


eqsat_basic = """(datatype Math
(Num i64)
(Var String)
(Add Math Math)
(Mul Math Math))


;; expr1 = 2 * (x + 3)
(let expr1 (Mul (Num 2) (Add (Var "x") (Num 3))))
;; expr2 = 6 + 2 * x
(let expr2 (Add (Num 6) (Mul (Num 2) (Var "x"))))


(rewrite (Add a b)
        (Add b a))
(rewrite (Mul a (Add b c))
        (Add (Mul a b) (Mul a c)))
(rewrite (Add (Num a) (Num b))
        (Num (+ a b)))
(rewrite (Mul (Num a) (Num b))
        (Num (* a b)))


(run 10)
(check (= expr1 expr2))
"""
egraph = egraph_from_egglog(eqsat_basic, "expr1", "Math")

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


@reset
def test_static_egraph():
    pass
