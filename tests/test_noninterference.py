import argparse
from runllm.constrained_decoding import RealizabilityChecker
from tests.utils import reset
from experiments.noninterference.noninterference import *


@reset
def test_noninterference():
    assert noninterference_checker.realizable("")
    assert noninterference_checker.realizable("skip")
    assert noninterference_checker.realizable("h := l; skip")
    assert not noninterference_checker.realizable("l := h")
    assert noninterference_checker.realizable("l := l - 634;")
    assert not noninterference_checker.realizable("l := l + h")
    assert noninterference_checker.realizable("if (l = 10) then {h := 1} else {l := ")
    assert not noninterference_checker.realizable("if (h = 10) then {l")
    assert noninterference_checker.realizable("while (h < 10) do {h := h + 1}")
    assert not noninterference_checker.realizable("while (h + l < 10) do {l := l + 1}")

@reset
def test_noninterference_large(n: int = 2):
    pref = ""
    for i in range(n):
        pref += f"while (h + l < 10 + {i}) do {{h := l + {i}}};"
    assert noninterference_checker.realizable(pref)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run performance noninterference test."
    )
    parser.add_argument(
        '-s', '--size',
        type=int, default=2,
        help='Run noninterference experiments with specified n'
    )
    args = parser.parse_args()
    test_noninterference_large(args.size)
