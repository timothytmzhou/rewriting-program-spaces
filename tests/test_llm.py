import greenery as grn
from core.parser import *
from lexing.leaves import RegexLeaf
from lexing.lexing import LexerSpec
from runllm.constrained_decoding import RealizabilityChecker
from runllm.run_llm import run_llm


def test_run_llm_simpl_gcd():
    lspec = LexerSpec({
        RegexLeaf("int", grn.parse("6"))
    })

    a = RealizabilityChecker(
        None,
        ConstantParser(RegexLeaf("int", grn.parse("6"))),
        lspec)
    prompt = "[INST] 3 + 3 = [/INST]"
    num = run_llm(a, prompt)[0]
    print(prompt + num)
