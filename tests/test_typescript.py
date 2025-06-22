from runllm.constrained_decoding import RealizabilityChecker
from tests.utils import reset
from experiments.typescript.typescript import *


ts_expression_grammar_checker = RealizabilityChecker(
    lambda x: x,
    exps(),
    lexer_spec,
)

ts_command_grammar_checker = RealizabilityChecker(
    lambda x: x,
    command_seqs(),
    lexer_spec,
)


@reset
def test_expression_grammar():
    assert ts_expression_grammar_checker.realizable("")
    assert ts_expression_grammar_checker.realizable("5 + 16")
    assert ts_expression_grammar_checker.realizable("albatross")
    assert ts_expression_grammar_checker.realizable("\"\"")
    assert ts_expression_grammar_checker.realizable("((a:number, b:string) => a + \"")
    assert ts_expression_grammar_checker.realizable("foo.bar.baz + bar(foo, 18)")
    assert not ts_expression_grammar_checker.realizable("5 + 10;")
    assert not ts_expression_grammar_checker.realizable("/16")
    assert not ts_expression_grammar_checker.realizable("if (h == 10) then {l")
    assert not ts_expression_grammar_checker.realizable("foo(,)")
    assert not ts_expression_grammar_checker.realizable(")")


@reset
def test_command_grammar():
    assert ts_command_grammar_checker.realizable("")
    assert ts_command_grammar_checker.realizable("5 + 16")
    assert ts_command_grammar_checker.realizable("5 + 16;")
    assert ts_command_grammar_checker.realizable("retu")
    assert ts_command_grammar_checker.realizable("let bln:boolean = ")
    assert ts_command_grammar_checker.realizable("{return alpha; return beta; {}")
    assert ts_command_grammar_checker.realizable(
        """function foo():(number, string) => boolean
        {return (n:number,s:string) => true;}"""
    )
    assert ts_command_grammar_checker.realizable(
        "if (false) 12; else function foo():number {retu"
    )
    assert not ts_command_grammar_checker.realizable("let x:noun")
    assert not ts_command_grammar_checker.realizable("}")
    assert not ts_command_grammar_checker.realizable("return return ")
    assert not ts_command_grammar_checker.realizable("function false ")
    assert not ts_command_grammar_checker.realizable("function foo():number => ")
    assert not ts_command_grammar_checker.realizable("if (h == 10) then {l")
    assert not ts_command_grammar_checker.realizable("foo(,)")
    assert not ts_command_grammar_checker.realizable(";")
