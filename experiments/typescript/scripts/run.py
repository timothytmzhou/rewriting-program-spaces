import argparse
from dataclasses import asdict
import os
import pandas as pd
from pathlib import Path
import time
from typing import Literal

from llm.realizability import RealizabilityChecker
from llm.run_llm import Config, LanguageModelRunner, ModelConfig
from tests.utils import reset
from experiments.typescript.compile_typescript import compile_typescript
from experiments.typescript.typescript_typechecker import typescript_typechecker
from experiments.typescript.typescript_abstract_syntax import typescript_grammar_checker

CONTEXT_FILE_PATH = "experiments/typescript/benchmarks/context.txt"
BENCHMARKS_FILE_PATH = "experiments/typescript/benchmarks/mbpp_benchmarks"


def ts_clean(initial_output: str) -> str:
    output = initial_output
    start_prog_index = initial_output.find('```')
    if start_prog_index != -1:
        output = initial_output[start_prog_index + 3:]
        end_prog_index = output.find('```')
        if end_prog_index != -1:
            output = output[:end_prog_index]
    return output


@reset
def run_experiment(
    prompt_name: str,
    temp: int,
    prompt: str,
    context: str,
    prompt_num: int,
    run_num: int,
    runner: LanguageModelRunner,
    config: Config,
    checker: RealizabilityChecker,
    outfile,
    outlist: list
):
    prompt = prompt.rstrip('\n')
    start = time.time()
    run_info = runner.run(config, prompt, context=context,
                          realizability_checker=checker)
    elapsed = time.time() - start
    # Check if program compiles with tsc
    compiled = compile_typescript(ts_clean(run_info.output))

    # Write Raw Output
    outfile.write(f"Prompt #: {prompt_num}, Run #: {run_num}\n")
    outfile.write(f"Raw Output: \n{run_info.output}\n")
    outfile.write(f"Processed Output: \n{ts_clean(run_info.output)}\n")
    outfile.write(f"Passed (if CD): {run_info.llm_finished}\n")
    outfile.write(f"Passed (tsc typechecker): {compiled}\n")
    outfile.write(f"Timed out: {run_info.timed_out}\n")
    outfile.write(f"Num Tokens Guessed: {run_info.num_tokens_guessed}\n")
    outfile.write(f"Num Tokens Generated: {run_info.num_tokens_generated}\n")
    outfile.write(
        f"Total Realizability Time: {run_info.total_realizability_time}")
    outfile.write(f"Total Time: {elapsed:.4f} seconds\n")
    outfile.write("=" * 40 + "\n")
    outfile.flush()
    os.fsync(outfile.fileno())

    outlist.append({
        'did_compile': compiled,
        'benchmark_id': prompt_num,
        'benchmark_name': prompt_name,
        'temperature': temp,
        'execution_time': elapsed,
        **asdict(run_info)
    })
    return


def run_typescript(runner: LanguageModelRunner, config: Config, runs: int,
                   mode: Literal['Unconstrained', 'GCD', 'TypedCD'],
                   model_name: str, output_directory: Path):
    # Set instrumentation
    match mode:
        case 'Unconstrained':
            checker = None
        case 'GCD':
            checker = typescript_grammar_checker
        case 'TypedCD':
            checker = typescript_typechecker
    results: list[dict] = []
    benchmark_dir = BENCHMARKS_FILE_PATH

    # Get llm context
    with open(CONTEXT_FILE_PATH, "r") as context_file:
        context = context_file.read().rstrip()

    for prompt_num, subdir in enumerate(os.listdir(benchmark_dir)):
        print(prompt_num, subdir, flush=True)
        if not os.path.isdir(os.path.join(benchmark_dir, subdir)):
            continue
        prompts_file = os.path.join(benchmark_dir, subdir, "prompt.txt")
        output_file = os.path.join(
            benchmark_dir, subdir,
            f"{mode}_results_temp_{config.temperature}_model_{model_name}.txt"
        )

        with open(prompts_file, "r") as promptfile, open(output_file, "w") as outfile:
            for run_num in range(runs):
                run_experiment(
                    subdir,
                    config.temperature,
                    promptfile.read().rstrip(),
                    context,
                    prompt_num,
                    run_num,
                    runner,
                    config,
                    checker,
                    outfile,
                    results
                )
    csv_path = output_directory / \
        f'{mode}_temp_{config.temperature}_model_{model_name}.csv'
    pd.DataFrame(results).to_csv(csv_path, index=False)
    return results


def main():
    valid_temps = [0.01, 0.3, 0.5, 0.7, 1.0]
    valid_models = {
        "llama13b": "codellama/CodeLlama-13b-Instruct-hf",
        "llama7b": "codellama/CodeLlama-7b-Instruct-hf",
        "deepseek": "deepseek-ai/deepseek-coder-6.7b-instruct",
    }
    valid_checkers = ["semantic", "unconstrained", "grammar"]
    checker_mapping = {
        "semantic": "TypedCD",
        "unconstrained": "Unconstrained", 
        "grammar": "GCD"
    }

    parser = argparse.ArgumentParser(
        description="Run typescript experiments."
    )
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
        "--checkers",
        nargs="+",
        choices=valid_checkers,
        default=valid_checkers,
        help="Which checker types to run (default: all).",
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=Path("experiments", "typescript", "generated_data"),
        help='Directory to store outputs'
    )
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)

    for model_name in args.models:
        model_config = ModelConfig(model_id=valid_models[model_name])
        model_runner = LanguageModelRunner(model_config=model_config)

        for temp in args.temps:
            for checker in args.checkers:
                run_typescript(
                    model_runner,
                    Config(temperature=temp, repetition_penalty=1.2, timeout=150),
                    1,
                    checker_mapping[checker],
                    model_name,
                    args.output
                )

        del model_runner


if __name__ == "__main__":
    main()
