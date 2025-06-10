import time
import argparse
import os

from runllm.run_llm import run_llm
from tests.utils import reset
from noninterference.noninterference import noninterference_checker


@reset
def run_experiment(prompt: str, context: str, prompt_num: int, run_num: int, checker, outfile):
    outfile.write(f"Prompt #: {prompt_num}, Run #: {run_num}\n") # Flush to outfile so results are visible
    outfile.flush()
    os.fsync(outfile.fileno())

    prompt = prompt.rstrip('\n')
    start_time = time.time()
    output = run_llm(checker, prompt, context)
    elapsed = time.time() - start_time
    outfile.write(f"Output: \n{output}\n")
    outfile.write(f"Time: {elapsed:.4f} seconds\n")
    outfile.write("=" * 40 + "\n")


def run_noninterference(runs: int):
    prompts_file = "noninterference/prompts.txt"
    output_file = "noninterference/results.txt"
    with open("noninterference/context.txt", "r") as context_file:
        context = context_file.read().rstrip()

    with open(prompts_file, "r") as promptfile, open(output_file, "w") as outfile:
        for prompt_num, prompt in enumerate(promptfile):
            if prompt and prompt.startswith("#"):
                continue
            for run_num in range(runs):
                run_experiment(prompt, context, prompt_num, run_num, noninterference_checker, outfile)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Run experiments with optional noninterference check."
    )
    parser.add_argument(
        '-n', '--noninterference',
        action='store_true', help='Run noninterference experiments'
    )
    args = parser.parse_args()
    if args.noninterference:
        run_noninterference(1)
