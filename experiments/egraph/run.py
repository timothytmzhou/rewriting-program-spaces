import re
import time
import pandas as pd
from dataclasses import replace
from pathlib import Path
from typing import Tuple
from core.rewrite import rewriter
from runllm.constrained_decoding import RealizabilityChecker
from runllm.run_llm import Config, LanguageModelRunner
from .egraph import egraph_from_egglog
from .let import let_equivalence, CodeBlock, let_lexer_spec
from tqdm import tqdm


BENCHMARKS_DIR = "experiments/egraph/benchmarks"
LET_EGGLOG_PATH = "experiments/egraph/let.egglog"


def load_file(filepath: str) -> str:
    with open(filepath, "r") as f:
        return f.read()


def get_benchmark_names():
    return [f.name for f in Path(BENCHMARKS_DIR).glob("*.egglog")]


def load_benchmark(name: str) -> Tuple[str, str]:
    content = load_file(f"{BENCHMARKS_DIR}/{name}")
    source = load_file(LET_EGGLOG_PATH)

    assert content.startswith(";; ")
    original = content.splitlines()[0][3:]
    source += content + "\n(run 100)"
    return original, source


def build_checker(source: str) -> RealizabilityChecker:
    egraph = egraph_from_egglog(source, "start", "Math")
    vars = re.findall(r'Var\s*"([^"]+)"', source)
    return RealizabilityChecker(
        lambda term: let_equivalence(egraph, term, frozenset(vars)),
        CodeBlock(),
        let_lexer_spec,
    )


def run_benchmark(
    config: Config,
    name: str,
    temp: float,
    runner,
    context: str,
    checker_type: str
) -> dict:
    original, source = load_benchmark(name)
    egraph_checker = build_checker(source)

    if checker_type == "constrained":
        checker = egraph_checker
    elif checker_type == "gcd":
        checker = RealizabilityChecker(lambda t: t, CodeBlock(), let_lexer_spec)
    else:
        checker = None

    prompt = f"The original program is:\n{original}"

    start = time.time()
    llm_finished, result = runner.run(config, prompt, context, checker)
    execution_time = time.time() - start
    success = egraph_checker.realizable(result, True) if llm_finished else False

    return {
        'benchmark': name,
        'temperature': temp,
        'success': success,
        'execution_time': execution_time,
        'result': result
    }


def run_experiment_type(runner, config, context, temps, checker_type: str) -> list:
    print(f"Running {checker_type} benchmarks")
    print("-------------------------")
    results = []
    benchmark_names = get_benchmark_names()

    total_iterations = len(temps) * len(benchmark_names)
    pbar = tqdm(total=total_iterations, desc=f"Running benchmarks: {checker_type}")
    for temp in temps:
        temp_config = replace(config, temperature=temp)
        for name in benchmark_names:
            results.append(run_benchmark(temp_config, name, temp, runner, context, checker_type))
            rewriter.clear()
            pbar.update(1)
    pbar.close()

    pd.DataFrame(results).to_csv(f'{checker_type}.csv', index=False)
    return results


def main():
    runner = LanguageModelRunner()
    temps = [.01, .3, .5, .7, 1.0]
    config = Config(num_guesses=300, max_new_tokens=100, repetition_penalty=1.2)
    context = load_file(f"{BENCHMARKS_DIR}/context.md")

    run_experiment_type(runner, config, context, temps, "constrained")
    run_experiment_type(runner, config, context, temps, "unconstrained")
    run_experiment_type(runner, config, context, temps, "gcd")


if __name__ == "__main__":
    main()
