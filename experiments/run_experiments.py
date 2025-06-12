import time
import argparse
import os
from dataclasses import dataclass

from experiments.utils.instrumenter import Instrumenter
from experiments.utils.totaler import get_tot_times_this_run
from runllm.constrained_decoding import RealizabilityChecker
from runllm.run_llm import Config, LanguageModelRunner
from tests.utils import reset
from noninterference.noninterference import noninterference_checker


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
    checker: RealizabilityChecker,
    inst: Instrumenter,
    outfile
):
    prompt = prompt.rstrip('\n')
    start = time.time()
    output = runner.run(checker, prompt, context)
    elapsed = time.time() - start

    # Perform instrumentation (check output, record times, etc.)
    inst.instrument(output)

    # Write Raw Output
    outfile.write(f"Prompt #: {prompt_num}, Run #: {run_num}\n")
    outfile.write(f"Output: \n{output}\n")
    outfile.write(f"Total Time: {elapsed:.4f} seconds\n")
    outfile.write(get_tot_times_this_run())
    outfile.write("=" * 40 + "\n")
    outfile.flush()
    os.fsync(outfile.fileno())


def run_noninterference(runner: LanguageModelRunner, runs: int):
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
                    noninterference_checker,
                    inst,
                    outfile
                )
    return inst


def run_noCD(runner: LanguageModelRunner, runs: int, foldername: str):
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
        num_runs: int = 1
):
    # Instantiate runner to load model
    runner = LanguageModelRunner(config)

    # Run experiments and write table
    # Implemented this way so table populates incrementally
    with open(outfile, "w") as out:
        out.write("\t\t\t\t\t\t\t\t# Progs Passing Constraints\t\t\t\t"
                  + "# Progs Passing Tests\t\t\t\t"
                  + "Avg Total Time (secs)\t\t\t\t"
                  + "Avg Time/Tok(secs)\n")
        if noninterference_CD:
            inst = run_noninterference(runner, num_runs)
            out.write("Noninterference[with our tool]\t\t\t\t" + inst.table_row())
            inst.clear()
        if noninterference_noCD:
            inst = run_noCD(runner, num_runs, "noninterference/")
            out.write("Noninterference[unconstrained]\t\t\t\t" + inst.table_row())
            inst.clear()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run experiments with optional noninterference check."
    )
    parser.add_argument(
        '-n', '--noninterference_CD',
        action='store_true', help='Run noninterference experiments'
    )
    parser.add_argument(
        '-r', '--noninterference_noCD',
        action='store_true', help='Run noninterference experiments'
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
        args.num_runs
    )
