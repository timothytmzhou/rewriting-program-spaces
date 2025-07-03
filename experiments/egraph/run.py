from typing import Tuple
from pathlib import Path
from runllm.constrained_decoding import RealizabilityChecker
from runllm.run_llm import Config, LanguageModelRunner
from .let import let_equivalence, Let, let_lexer_spec
from .egraph import egraph_from_egglog


BENCHMARKS_DIR = "experiments/egraph/benchmarks"
LET_EGGLOG_PATH = "experiments/egraph/let.egglog"


def load_file(filepath: str) -> str:
    with open(filepath, "r") as f:
        return f.read()


def load_and_prepare_benchmark(benchmark_name: str) -> Tuple[str, RealizabilityChecker]:
    # Load benchmark egglog
    benchmark_path = f"{BENCHMARKS_DIR}/{benchmark_name}"
    benchmark_content = load_file(benchmark_path)
    # Load let.egglog
    source = load_file(LET_EGGLOG_PATH)

    assert benchmark_content.startswith(";; ")
    original_program = benchmark_content.splitlines()[0][3:]
    source += benchmark_content
    source += "\n(run 100)"
    egraph = egraph_from_egglog(source, "start", "Math")
    checker = RealizabilityChecker(
        lambda term: let_equivalence(egraph, term),
        Let(),
        let_lexer_spec,
    )
    return original_program, checker


def get_benchmark_names():
    return [
        benchmark_file.name
        for benchmark_file in Path(BENCHMARKS_DIR).glob("*.egglog")
    ]


def main():
    context = load_file(f"{BENCHMARKS_DIR}/context.md")
    config = Config(temperature=0.00001,
                    num_guesses=1000, max_new_tokens=100)
    runner = LanguageModelRunner(config)

    for benchmark in get_benchmark_names():
        original_program, checker = load_and_prepare_benchmark(benchmark)
        prompt = f"The original program is:\n{original_program}"
        print(prompt)
        print(runner.run(checker, prompt, context))


if __name__ == "__main__":
    main()
