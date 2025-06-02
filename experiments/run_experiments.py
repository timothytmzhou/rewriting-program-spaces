import time
import argparse

from runllm.run_llm import run_llm
from noninterference.noninterference import noninterference_checker


def run_experiment(prompt: str, prompt_num: int, run_num: int, checker, outfile):
    prompt = prompt.rstrip('\n')
    start_time = time.time()
    output = run_llm(checker, prompt)
    elapsed = time.time() - start_time
    outfile.write(f"Prompt #: {prompt_num}, Run #: {run_num}\n")
    outfile.write(f"Output: {output}\n")
    outfile.write(f"Time: {elapsed:.4f} seconds\n")
    outfile.write("=" * 40 + "\n")


def run_noninterference(runs: int):
    input_file = "noninterference/prompts.txt"
    output_file = "results.txt"

    with open(input_file, "r") as infile, open(output_file, "w") as outfile:
        for prompt_num, prompt in enumerate(infile):
            for run_num in range(runs):
                run_experiment(prompt, prompt_num, run_num, noninterference_checker, outfile)


def main():
    parser = argparse.ArgumentParser(
        description="Run experiments with optional noninterference check."
    )
    parser.add_argument(
        '-n', '--noninterference',
        action='store_true', help='Run noninterference experiments'
    )
    args = parser.parse_args()
    print(vars(args))
    if args["noninterference"]:
        print("q")
        run_noninterference(10)


if __name__ == "main":
    print("hi")
    main()
