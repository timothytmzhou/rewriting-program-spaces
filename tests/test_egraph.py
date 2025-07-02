from experiments.egraph.run import *
from runllm.constrained_decoding import RealizabilityChecker
from tests.utils import reset
from experiments.egraph.let import *
from experiments.egraph.egraph import *
import pytest
from pathlib import Path


with open("experiments/egraph/let.egglog", "r") as f:
    eqsat_basic = f.read()

egraph_expression_grammar_checker = RealizabilityChecker(
    lambda x: x,
    Let(),
    let_lexer_spec,
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

    assert not egraph_expression_grammar_checker.realizable("+ x")
    assert not egraph_expression_grammar_checker.realizable("let =")
    assert not egraph_expression_grammar_checker.realizable(")")
    assert not egraph_expression_grammar_checker.realizable("()")


six_source = """
(let six (Num 6))
(let times (Mul (Num 3) (Num 2)))
(let add (Add (Num 3) (Num 3)))
(let div (Div (Num 6) (Num 1)))
(rewrite (Num 6) (Var "x"))
(run 100)
"""
six_source = eqsat_basic + six_source
six_egraph = egraph_from_egglog(six_source, "six", "Math")


@reset
def test_static_egraph():
    checker = RealizabilityChecker(
        in_egraph(six_egraph),
        Let(),
        let_lexer_spec,
    )
    assert checker.realizable("")
    assert checker.realizable("6")
    assert checker.realizable("3 * 2")
    assert checker.realizable("3 *")
    assert checker.realizable("3 + ")
    assert checker.realizable("x")
    # egraph doesn't have certain constants in it, so these are not realizable
    assert not checker.realizable("2 +")
    assert not checker.realizable("x +")


@reset
def test_dynamic_egraph():
    checker = RealizabilityChecker(
        lambda t: let_equivalence(six_egraph, t),
        Let(),
        let_lexer_spec,
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
    assert not checker.realizable("x +")


@reset
def test_div():
    source = """
    (let div (Div (Mul (Var "a") (Var "b")) (Mul (Var "c") (Var "d"))))
    (run 100)
    """
    source = eqsat_basic + source
    egraph = egraph_from_egglog(source, "div", "Math")
    checker = RealizabilityChecker(
        lambda t: let_equivalence(egraph, t),
        Let(),
        let_lexer_spec,
    )
    assert checker.realizable("(a * b) / (c * d)")
    assert checker.realizable("(a * b) * (1 / (c * d))")
    assert checker.realizable("a * (b / (c * d))")
    assert checker.realizable("(a / c) * (b / d)")
    assert not checker.realizable("c")


def get_benchmark_names():
    return [
        benchmark_file.name
        for benchmark_file in Path(BENCHMARKS_DIR).glob("*.egglog")
    ]


@pytest.mark.parametrize("benchmark_name", get_benchmark_names())
@reset
def test_benchmark(benchmark_name):
    program_header, checker = load_and_prepare_benchmark(benchmark_name)
    assert checker.realizable(program_header)
