import time
import argparse
import os
from dataclasses import asdict, replace
from typing import Literal
import pandas as pd

from runllm.constrained_decoding import RealizabilityChecker
from runllm.run_llm import Config, LanguageModelRunner, ModelConfig
from tests.utils import reset
# from noninterference.noninterference import noninterference_checker
from typescript.compile_typescript import compile_typescript
from typescript.typescript_typechecker import (typescript_typechecker,
                                               typescript_grammar_checker)


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
    outfile.write(f"Total Realizability Time: {run_info.total_realizability_time}")
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
                   model_name: str):
    # Set instrumentation
    match mode:
        case 'Unconstrained':
            checker = None
        case 'GCD':
            checker = typescript_grammar_checker
        case 'TypedCD':
            checker = typescript_typechecker
    results: list[dict] = []
    benchmark_dir = "typescript/benchmarks/mbpp_benchmarks"

    # Get llm context
    with open("typescript/benchmarks/context.txt", "r") as context_file:
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
    pd.DataFrame(results).to_csv(f'{mode}_temp_{TEMP}_model_{model_name}.csv',
                                 index=False)
    return results


# def run_noninterference(runner: LanguageModelRunner, config: Config, runs: int):
#     # Set instrumentation
#     inst: Instrumenter = Instrumenter()

#     # Get llm context
#     prompts_file = "noninterference/prompts.txt"
#     output_file = "noninterference/results.txt"
#     with open("noninterference/context.txt", "r") as context_file:
#         context = context_file.read().rstrip()

#     # Run experiments
#     with open(prompts_file, "r") as promptfile, open(output_file, "a") as outfile:
#         for prompt_num, prompt in enumerate(promptfile):
#             if prompt and prompt.startswith("#"):
#                 continue
#             for run_num in range(runs):
#                 inst.set_indices(prompt_num, run_num)
#                 run_experiment(
#                     prompt,
#                     context,
#                     prompt_num,
#                     run_num,
#                     runner,
#                     config,
#                     noninterference_checker,
#                     inst,
#                     outfile
#                 )
#     return inst


# def run_noninterference_noCD(runner: LanguageModelRunner, config: Config,
#                              runs: int, foldername: str):
#     # Set instrumentation
#     checker = None
#     inst: Instrumenter = Instrumenter()

#     # Get llm context
#     prompts_file = foldername + "prompts.txt"
#     output_file = foldername + "results_raw.txt"
#     with open(foldername + "context.txt", "r") as context_file:
#         context = context_file.read().rstrip()

#     # Run experiments
#     with open(prompts_file, "r") as promptfile, open(output_file, "w") as outfile:
#         for prompt_num, prompt in enumerate(promptfile):
#             if prompt and prompt.startswith("#"):
#                 continue
#             for run_num in range(runs):
#                 inst.set_indices(prompt_num, run_num)
#                 run_experiment(
#                     prompt,
#                     context,
#                     prompt_num,
#                     run_num,
#                     runner,
#                     config,
#                     checker,
#                     inst,
#                     outfile
#                 )

#     return inst


def run_experiments(
        model_name: str,
        model_config: ModelConfig,
        config: Config,
        outfile,
        noninterference_CD: bool,
        noninterference_noCD: bool,
        typescript_CD: bool,
        typescript_noCD: bool,
        typescript_GCD: bool,
        performance: bool,
        num_runs: int = 1,
):
    runner = LanguageModelRunner(model_config=model_config)
    # Run experiments
    # if noninterference_CD:
    #     run_noninterference(runner, config, num_runs)
    # if noninterference_noCD:
    #     run_noninterference_noCD(runner, config, num_runs,
    #                                     "noninterference/")
    if typescript_CD:
        run_typescript(runner, config, num_runs, 'TypedCD', model_name)
    if typescript_noCD:
        run_typescript(runner, config, num_runs, 'Unconstrained', model_name)
    if typescript_GCD:
        run_typescript(runner, config, num_runs, 'GCD', model_name)
    del runner


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run experiments with optional noninterference check."
    )
    parser.add_argument(
        '-n', '--noninterference_CD',
        action='store_true', help='Run noninterference experiments with our decoding'
    )
    parser.add_argument(
        '-r', '--noninterference_noCD',
        action='store_true', help='Run noninterference experiments without our decoding'
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
        '-p', '--performance',
        action='store_true', help='Run performance experiments'
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
            f"table_temp_{TEMP}_model_{model_name}.txt",
            args.noninterference_CD,
            args.noninterference_noCD,
            args.typescript_CD,
            args.typescript_noCD,
            args.typescript_GCD,
            args.performance,
            args.num_runs,
            # seed=3587551093
        )
