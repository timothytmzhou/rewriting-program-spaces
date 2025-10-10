import argparse
import random
import re
import time
from dataclasses import asdict, replace
from pathlib import Path
from typing import Tuple

import numpy as np
import pandas as pd
import torch
from tqdm import tqdm

from core.rewrite import rewriter
from llm.realizability import RealizabilityChecker
from llm.run_llm import Config, LanguageModelRunner, ModelConfig

from ..egraph import egraph_from_egglog
from ..let import code_block_grammar, let_equivalence, let_grammar, let_lexer_spec

# make everything deterministic
torch.manual_seed(0)
random.seed(0)
np.random.seed(0)

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


def build_checker(source: str, code_block=False) -> RealizabilityChecker:
    egraph = egraph_from_egglog(source, "start", "Math")
    vars = re.findall(r'Var\s*"([^"]+)"', source)
    grammar = code_block_grammar if code_block else let_grammar
    return RealizabilityChecker(
        lambda term: let_equivalence(egraph, term, frozenset(vars)),
        grammar,
        let_lexer_spec,
    )


def run_benchmark(
    config: Config,
    name: str,
    temp: float,
    runner,
    context: str,
    checker_type: str,
    code_block: bool,
) -> dict:
    original, source = load_benchmark(name)
    egraph_checker = build_checker(source, code_block=code_block)

    if checker_type == "constrained":
        checker = egraph_checker
    elif checker_type == "gcd":
        grammar = code_block_grammar if code_block else let_grammar
        checker = RealizabilityChecker(lambda t: t, grammar, let_lexer_spec)
    elif checker_type == "unconstrained":
        checker = None
    else:
        raise ValueError(f"Unknown checker type: {checker_type}")

    prompt = f"The original program is:\n{original}"

    start = time.time()
    run_info = runner.run(config, prompt, context, checker)
    execution_time = time.time() - start
    success = (
        egraph_checker.realizable(run_info.output, True)
        if run_info.llm_finished
        else False
    )

    return {
        "success": success,
        "benchmark": name,
        "temperature": temp,
        "execution_time": execution_time,
        **asdict(run_info),
    }


def run_experiment_type(
    output: Path,
    runner,
    config,
    temps,
    checker_type,
    log_name,
    code_block=False,
) -> list:
    print(f"Running {checker_type} benchmarks")
    print("-------------------------")
    context = load_file(f"{BENCHMARKS_DIR}/context.md")
    if code_block:
        context += "Start and end your solution with a codeblock using ```.\n"

    results = []
    benchmark_names = get_benchmark_names()

    total_iterations = len(temps) * len(benchmark_names)
    pbar = tqdm(total=total_iterations, desc=f"Running benchmarks: {checker_type}")
    for temp in temps:
        temp_config = replace(config, temperature=temp)
        for name in benchmark_names:
            results.append(
                run_benchmark(
                    temp_config, name, temp, runner, context, checker_type, code_block
                )
            )
            rewriter.clear()
            pbar.update(1)
    pbar.close()

    pd.DataFrame(results).to_csv(output / f"{log_name}-{checker_type}.csv", index=False)
    return results


def parse_delimit(value: str):
    v = value.lower()
    if v == "yes":
        return [True]
    elif v == "no":
        return [False]
    elif v == "both":
        return [True, False]
    else:
        raise argparse.ArgumentTypeError(
            "delimit must be one of: 'yes', 'no', or 'both'"
        )


def main():
    valid_temps = [0.01, 0.3, 0.5, 0.7, 1.0]
    valid_models = {
        "llama13b": "codellama/CodeLlama-13b-Instruct-hf",
        "llama7b": "codellama/CodeLlama-7b-Instruct-hf",
        "deepseek": "deepseek-ai/deepseek-coder-6.7b-instruct",
    }
    valid_checkers = ["semantic", "unconstrained", "grammar"]
    checker_mapping = {
        "semantic": "constrained",
        "unconstrained": "unconstrained",
        "grammar": "gcd"
    }

    parser = argparse.ArgumentParser(description="Run egraph experiments.")
    parser.add_argument(
        "--models",
        nargs="+",
        choices=valid_models.keys(),
        default=list(valid_models.keys()),
        help="Which models to run (default: all).",
    )
    parser.add_argument(
        "--temps",
        nargs="+",
        type=float,
        choices=valid_temps,
        default=valid_temps,
        help="Which temperatures to run (default: all).",
    )

    parser.add_argument(
        "--delimit",
        type=parse_delimit,
        default=[True, False],
        help="Run with delimiters: yes, no, or both (default: both).",
    )
    parser.add_argument(
        "--checkers",
        nargs="+",
        choices=valid_checkers,
        default=valid_checkers,
        help="Which checker types to run (default: all).",
    )

    parser.add_argument(
        "--output",
        type=Path,
        default=Path("experiments", "egraph", "data"),
        help="Path to the output directory (default: experiments/egraph/data).",
    )

    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    # --- Configuration ---
    config = Config(num_guesses=300, max_new_tokens=100, repetition_penalty=1.2)

    # --- Run experiments ---
    for model_name in args.models:
        model_config = ModelConfig(model_id=valid_models[model_name])
        runner = LanguageModelRunner(model_config)

        for code_block in args.delimit:
            for checker_type in args.checkers:
                name = f"{model_name}"
                if code_block:
                    name += "-codeblock"

                run_experiment_type(
                    args.output,
                    runner,
                    config,
                    args.temps,
                    checker_mapping[checker_type],
                    name,
                    code_block,
                )

        del runner  # Free up memory


if __name__ == "__main__":
    main()
