from pathlib import Path
import time
import argparse
import os
from dataclasses import asdict, replace
from typing import Literal
import pandas as pd

from llm.realizability import RealizabilityChecker
from llm.run_llm import Config, LanguageModelRunner, ModelConfig
from tests.utils import reset
from experiments.typescript.compile_typescript import compile_typescript
from experiments.typescript.typescript_typechecker import typescript_typechecker
from experiments.typescript.typescript_abstract_syntax import typescript_grammar_checker

CONTEXT_FILE_PATH = "../benchmarks/context.txt"
BENCHMARKS_FILE_PATH = "../benchmarks/mbpp_benchmarks"


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
                          realizability_checker=checker, timeout=1000)
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
        output_file = os.path.join(benchmark_dir, subdir,
                                   f"{mode}_results_temp_{TEMP}_model_{model_name}.txt")

        with open(prompts_file, "r") as promptfile, open(output_file, "w") as outfile:
            for run_num in range(runs):
                run_experiment(
                    subdir,
                    TEMP,
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
    csv_path = output_directory / f'{mode}_temp_{TEMP}_model_{model_name}.csv'
    pd.DataFrame(results).to_csv(csv_path, index=False)
    return results


def run_experiments(
        model_name: str,
        model_config: ModelConfig,
        config: Config,
        typescript_CD: bool,
        typescript_noCD: bool,
        typescript_GCD: bool,
        output_directory: Path,
        num_runs: int = 1,
):
    runner = LanguageModelRunner(model_config=model_config)
    if typescript_CD:
        run_typescript(
            runner, config, num_runs, 'TypedCD', model_name, output_directory
        )
    if typescript_noCD:
        run_typescript(
            runner, config, num_runs, 'Unconstrained', model_name, output_directory
        )
    if typescript_GCD:
        run_typescript(
            runner, config, num_runs, 'GCD', model_name, output_directory
        )
    del runner


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run experiments with optional noninterference check."
    )
    parser.add_argument(
        '-t', '--typescript_CD',
        action='store_true', help='Run typescript experiments with our decoding'
    )
    parser.add_argument(
        '-o', '--typescript_noCD',
        action='store_true', help='Run typescript experiments without our decoding'
    )
    parser.add_argument(
        '-g', '--typescript_GCD',
        action='store_true', help='Run typescript experiments with GCD'
    )
    parser.add_argument(
        '--num_runs',
        type=int,
        default=1,
        help='Number of runs for each prompt (default: 1)'
    )
    parser.add_argument(
        '--temp',
        type=float,
        default=1.0,
        help='LLM Temperature (default: 1.0)'
    )
    parser.add_argument(
        '--output',
        type=Path,
        default=".",
        help='Directory to store outputs'
    )
    args = parser.parse_args()
    TEMP: float = float(args.temp)

    # Instantiate runner to load model
    models = [
        ("llama7b", ModelConfig(model_id="codellama/CodeLlama-7b-Instruct-hf")),
        ("deepseek-coder",
         ModelConfig(model_id="deepseek-ai/deepseek-coder-6.7b-instruct")),
        ("llama13b", ModelConfig(model_id="codellama/CodeLlama-13b-Instruct-hf")),
    ]

    for (model_name, model_config) in models:
        run_experiments(
            model_name,
            model_config,
            replace(Config(), temperature=TEMP, repetition_penalty=1.2),
            args.typescript_CD,
            args.typescript_noCD,
            args.typescript_GCD,
            args.output,
            args.num_runs,
            # seed=3587551093
        )
