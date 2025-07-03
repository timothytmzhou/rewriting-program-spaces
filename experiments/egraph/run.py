from typing import Tuple
from pathlib import Path
import time
import pandas as pd
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


def run_experiment():
    TEMPERATURES = [0.01, 0.3, 0.5, 0.7, 1.0]
    context = load_file(f"{BENCHMARKS_DIR}/context.md")
    constrained_results = []
    unconstrained_results = []

    for temp in TEMPERATURES:
        config = Config(
            temperature=temp,
            num_guesses=1000,
            max_new_tokens=100,
            repetition_penalty=1.0
        )
        runner = LanguageModelRunner(config)

        for benchmark in get_benchmark_names():
            original_program, checker = load_and_prepare_benchmark(benchmark)
            prompt = f"The original program is:\n{original_program}"

            # Run with checker (constrained)
            start_time = time.time()
            try:
                result_with_checker = runner.run(prompt, context, checker)
            except BaseException as e:
                print(e)
                result_with_checker = None
            constrained_execution_time = time.time() - start_time

            constrained_results.append({
                'benchmark': benchmark,
                'temperature': temp,
                'success': result_with_checker is not None,
                'execution_time': constrained_execution_time,
                'result': result_with_checker
            })

            # Run without checker (unconstrained baseline)
            start_time = time.time()
            result_without_checker = runner.run(prompt, context, None)
            unconstrained_execution_time = time.time() - start_time

            unconstrained_results.append({
                'benchmark': benchmark,
                'temperature': temp,
                'execution_time': unconstrained_execution_time,
                'result': result_without_checker
            })

    # Save results
    constrained_df = pd.DataFrame(constrained_results)
    constrained_df.to_csv('egraph_constrained_results.csv', index=False)

    unconstrained_df = pd.DataFrame(unconstrained_results)
    unconstrained_df.to_csv('egraph_unconstrained_results.csv', index=False)

    return constrained_df, unconstrained_df


def main():
    run_experiment()


if __name__ == "__main__":
    main()
