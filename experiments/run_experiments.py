import time
import argparse
import os
from dataclasses import dataclass
from typing import Optional
from transformers import set_seed

from experiments.utils.instrumenter import Instrumenter
from runllm.constrained_decoding import RealizabilityChecker
from runllm.run_llm import Config, LanguageModelRunner
from tests.utils import reset
from noninterference.noninterference import noninterference_checker
from typescript.typescript_instrumeter import TypescriptInstrumeter
from typescript.typescript_typechecker import typescript_checker


@dataclass
class TrivialChecker:

    def realizable(self, pref: str, final: bool = False) -> bool:
        return True


@reset
def run_experiment(
    prompt: str,
    context: str,
    prompt_num: int,
    run_num: int,
    runner: LanguageModelRunner,
    config: Config,
    checker: RealizabilityChecker,
    inst: Instrumenter,
    outfile
):
    prompt = prompt.rstrip('\n')
    start = time.time()
    passed, output = runner.run(config, prompt, context=context,
                                realizability_checker=checker)
    elapsed = time.time() - start

    # Extract program and perform instrumentation (check output, record times, etc.)
    assert isinstance(output, str)
    start_prog_index = output.find('```')
    if start_prog_index != -1:
        output = output[start_prog_index + 3:]
        end_prog_index = output.find('```')
        if end_prog_index != -1:
            output = output[:end_prog_index]
    inst.instrument(output, passed)

    # Write Raw Output
    outfile.write(f"Prompt #: {prompt_num}, Run #: {run_num}\n")
    outfile.write(f"Output: \n{output}\n")
    outfile.write(f"Total Time: {elapsed:.4f} seconds\n")
    outfile.write(inst.get_tot_times_this_run())
    outfile.write("=" * 40 + "\n")
    outfile.flush()
    print(f"{output}\n")
    os.fsync(outfile.fileno())


def run_typescript(runner: LanguageModelRunner, config: Config, runs: int):
    # Set instrumentation
    inst: Instrumenter = TypescriptInstrumeter(typescript_checker)
    benchmark_dir = "typescript/benchmarks/mbpp_benchmarks"

    # Get llm context
    with open("typescript/benchmarks/context.txt", "r") as context_file:
        context = context_file.read().rstrip()

    for prompt_num, subdir in enumerate(os.listdir(benchmark_dir)):
        print(prompt_num, subdir)
        if not os.path.isdir(os.path.join(benchmark_dir, subdir)):
            continue
        prompts_file = os.path.join(benchmark_dir, subdir, "prompt.txt")
        output_file = os.path.join(benchmark_dir, subdir, "CD_results.txt")

        with open(prompts_file, "r") as promptfile, open(output_file, "w") as outfile:
            for run_num in range(runs):
                inst.set_indices(prompt_num, run_num)
                run_experiment(
                    promptfile.read().rstrip(),
                    context,
                    prompt_num,
                    run_num,
                    runner,
                    config,
                    typescript_checker,
                    inst,
                    outfile
                )
    return inst


def run_noninterference(runner: LanguageModelRunner, config: Config, runs: int):
    # Set instrumentation
    inst: Instrumenter = Instrumenter(noninterference_checker)

    # Get llm context
    prompts_file = "noninterference/prompts.txt"
    output_file = "noninterference/results.txt"
    with open("noninterference/context.txt", "r") as context_file:
        context = context_file.read().rstrip()

    # Run experiments
    with open(prompts_file, "r") as promptfile, open(output_file, "a") as outfile:
        for prompt_num, prompt in enumerate(promptfile):
            if prompt and prompt.startswith("#"):
                continue
            for run_num in range(runs):
                inst.set_indices(prompt_num, run_num)
                run_experiment(
                    prompt,
                    context,
                    prompt_num,
                    run_num,
                    runner,
                    config,
                    noninterference_checker,
                    inst,
                    outfile
                )
    return inst


def run_typescript_noCD(runner: LanguageModelRunner, config: Config, runs: int):
    # Set instrumentation
    checker = TrivialChecker()
    inst: Instrumenter = TypescriptInstrumeter(typescript_checker)
    benchmark_dir = "typescript/benchmarks/mbpp_benchmarks"

    # Get llm context
    with open("typescript/benchmarks/context.txt", "r") as context_file:
        context = context_file.read().rstrip()

    for prompt_num, subdir in enumerate(os.listdir(benchmark_dir)):
        print(prompt_num, subdir)
        if not os.path.isdir(os.path.join(benchmark_dir, subdir)):
            continue
        prompts_file = os.path.join(benchmark_dir, subdir, "prompt.txt")
        output_file = os.path.join(benchmark_dir, subdir, "noCD_results.txt")

        with open(prompts_file, "r") as promptfile, open(output_file, "w") as outfile:
            for run_num in range(runs):
                inst.set_indices(prompt_num, run_num)
                run_experiment(
                    promptfile.read().rstrip(),
                    context,
                    prompt_num,
                    run_num,
                    runner,
                    config,
                    checker,
                    inst,
                    outfile
                )
    return inst


def run_noninterference_noCD(runner: LanguageModelRunner, config: Config,
                             runs: int, foldername: str):
    # Set instrumentation
    checker = TrivialChecker()
    inst: Instrumenter = Instrumenter(noninterference_checker)

    # Get llm context
    prompts_file = foldername + "prompts.txt"
    output_file = foldername + "results_raw.txt"
    with open(foldername + "context.txt", "r") as context_file:
        context = context_file.read().rstrip()

    # Run experiments
    with open(prompts_file, "r") as promptfile, open(output_file, "w") as outfile:
        for prompt_num, prompt in enumerate(promptfile):
            if prompt and prompt.startswith("#"):
                continue
            for run_num in range(runs):
                inst.set_indices(prompt_num, run_num)
                run_experiment(
                    prompt,
                    context,
                    prompt_num,
                    run_num,
                    runner,
                    config,
                    checker,
                    inst,
                    outfile
                )

    return inst


def run_experiments(
        config: Config,
        outfile,
        noninterference_CD: bool,
        noninterference_noCD: bool,
        typescript_CD: bool,
        typescript_noCD: bool,
        performance: bool,
        num_runs: int = 1,
        seed: Optional[int] = None
):
    # Instantiate runner to load model
    if seed is not None:
        set_seed(seed)
    runner = LanguageModelRunner()

    # Run experiments and write table
    # Implemented this way so table populates incrementally
    with open(outfile, "w") as out:
        out.write("\t\t\t\t\t\t\t\t# Progs Passing Constraints\t\t\t\t"
                  + "# Progs Passing Tests\t\t\t\t"
                  + "Avg Total Time (secs)\t\t\t\t"
                  + "Avg Time/Tok(secs)\n")
        if noninterference_CD:
            inst = run_noninterference(runner, config, num_runs)
            out.write("Noninterference[with our tool]\t\t\t\t" + inst.table_row())
            inst.clear()
        if noninterference_noCD:
            inst = run_noninterference_noCD(runner, config, num_runs,
                                            "noninterference/")
            out.write("Noninterference[unconstrained]\t\t\t\t" + inst.table_row())
            inst.clear()
        if typescript_CD:
            inst = run_typescript(runner, config, num_runs)
            out.write("Typescript[with our tool]\t\t\t\t" + inst.table_row())
            inst.clear()
        if typescript_noCD:
            inst = run_typescript_noCD(runner, config, num_runs)
            out.write("Typescript[unconstrained]\t\t\t\t" + inst.table_row())
            inst.clear()


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
        '-p', '--performance',
        action='store_true', help='Run performance experiments'
    )
    parser.add_argument(
        '--num_runs',
        type=int,
        default=1,
        help='Number of runs for each prompt (default: 1)'
    )
    args = parser.parse_args()
    run_experiments(
        Config(),
        "table.txt",
        args.noninterference_CD,
        args.noninterference_noCD,
        args.typescript_CD,
        args.typescript_noCD,
        args.performance,
        args.num_runs,
        seed=3587551093
    )
