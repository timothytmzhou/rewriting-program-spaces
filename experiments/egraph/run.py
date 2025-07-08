import re
import time
import pandas as pd
from dataclasses import replace, asdict
from pathlib import Path
from typing import Tuple
from core.rewrite import rewriter
from runllm.constrained_decoding import RealizabilityChecker
from runllm.run_llm import Config, LanguageModelRunner, ModelConfig
from .egraph import egraph_from_egglog
from .let import let_equivalence, Let, CodeBlock, let_lexer_spec
from tqdm import tqdm
import torch
import random
import numpy as np

# make everything deterministic
torch.manual_seed(0)
random.seed(0)
np.random.seed(0)
torch.use_deterministic_algorithms(True)

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
    grammar = CodeBlock() if code_block else Let()
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
    code_block: bool
) -> dict:
    original, source = load_benchmark(name)
    egraph_checker = build_checker(source, code_block=code_block)

    if checker_type == "constrained":
        checker = egraph_checker
    elif checker_type == "gcd":
        grammar = CodeBlock() if code_block else Let()
        checker = RealizabilityChecker(lambda t: t, grammar, let_lexer_spec)
    elif checker_type == "unconstrained":
        checker = None
    else:
        raise ValueError(f"Unknown checker type: {checker_type}")

    prompt = f"The original program is:\n{original}"

    start = time.time()
    run_info = runner.run(config, prompt, context, checker)
    execution_time = time.time() - start
    success = egraph_checker.realizable(
        run_info.output, True) if run_info.llm_finished else False

    return {
        'success': success,
        'benchmark': name,
        'temperature': temp,
        'execution_time': execution_time,
        **asdict(run_info)
    }


def run_experiment_type(runner, config, temps, checker_type, log_name, code_block=False) -> list:
    print(f"Running {checker_type} benchmarks")
    print("-------------------------")
    context = load_file(f"{BENCHMARKS_DIR}/context.md")
    if code_block:
        context += "Start and end your solution with a codeblock using ```.\n"

    results = []
    benchmark_names = get_benchmark_names()

    total_iterations = len(temps) * len(benchmark_names)
    pbar = tqdm(total=total_iterations,
                desc=f"Running benchmarks: {checker_type}")
    for temp in temps:
        temp_config = replace(config, temperature=temp)
        for name in benchmark_names:
            results.append(run_benchmark(temp_config, name, temp,
                           runner, context, checker_type, code_block))
            rewriter.clear()
            pbar.update(1)
    pbar.close()

    pd.DataFrame(results).to_csv(f'{log_name}-{checker_type}.csv', index=False)
    return results


def main():
    temps = [.01, .3, .5, .7, 1.0]
    config = Config(
        num_guesses=300,
        max_new_tokens=100,
        repetition_penalty=1.2
    )

    models = [
        ("llama13b", ModelConfig(model_id="codellama/CodeLlama-13b-Instruct-hf")),
        ("llama7b", ModelConfig(model_id="codellama/CodeLlama-7b-Instruct-hf")),
        ("deepseek-coder", ModelConfig(model_id="deepseek-ai/deepseek-coder-6.7b-instruct")),
    ]

    for (model_name, model_config) in models:
        runner = LanguageModelRunner(model_config)
        for code_block in [False, True]:
            for checker_type in ["constrained", "unconstrained", "gcd"]:
                name = f"{model_name}"
                if code_block:
                    name += "-codeblock"
                run_experiment_type(
                    runner,
                    config,
                    temps,
                    checker_type,
                    name,
                    code_block
                )
        del runner  # Free up memory


if __name__ == "__main__":
    main()
