import greenery as grn
from core.parser import *
from lexing.leaves import RegexLeaf
from lexing.lexing import LexerSpec
from runllm.constrained_decoding import RealizabilityChecker
from runllm.run_llm import run_llm


def test_run_llm_simpl_gcd():
    lspec = LexerSpec({
        RegexLeaf("6", grn.parse("6"))
    })

    a = RealizabilityChecker(
        None,
        ConstantParser(RegexLeaf("6", grn.parse("6"))),
        None,
        None,
        lspec)
    print(run_llm(a, "My favorite number is "))
