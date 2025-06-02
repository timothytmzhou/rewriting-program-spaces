from runllm.constrained_decoding import RealizabilityChecker
from tests.utils import reset
from experiments.noninterference.noninterference import *


@reset
def test_noninterference():
    noninterference_checker = RealizabilityChecker(
        lambda asts: secure_cmds(asts, SecurityLevel.LOW), commands(), lexer_spec
    )
    assert noninterference_checker.realizable("")
    assert noninterference_checker.realizable("skip")
    assert noninterference_checker.realizable("h := l; skip")
    assert not noninterference_checker.realizable("l := h")
    assert noninterference_checker.realizable("l := l + 634;")
    assert not noninterference_checker.realizable("l := l + h")
    assert noninterference_checker.realizable("if l = 10 then h := 1 else l := 1")
    assert not noninterference_checker.realizable("if h = 10 then h := 1 else l := 1")
    assert noninterference_checker.realizable("while h < 10 do h := h + 1")
    assert not noninterference_checker.realizable("while h + l < 10 do l := l + 1")
