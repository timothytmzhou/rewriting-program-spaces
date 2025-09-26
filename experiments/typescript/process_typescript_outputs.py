import csv
import os
import re
from func_timeout import func_timeout, FunctionTimedOut
import pandas as pd

from compile_typescript import *

MY_ROOT_DIR = "/home/ubuntu/"


# # # HELPER FUNCTIONS # # #
def compile_csv(csv_path):
    compiled_filenames = []
    programs_to_test = []
    test_cases = []
    os.makedirs(csv_path[:-4], exist_ok=True)

    print(csv_path)
    with open(csv_path, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            did_compile = row['did_compile'].lower() == 'true'
            if not did_compile:
                continue
            output = row['output']
            benchmark_name = row['benchmark_name']
            subdir = os.path.join(
                os.getcwd(), 'benchmarks', 'mbpp_benchmarks', benchmark_name
            )
            tests_path = os.path.join(subdir, 'test.ts')
            if os.path.exists(tests_path):
                with open(tests_path, 'r', encoding='utf-8') as f:
                    tests = f.read()
                    programs_to_test.append(output.replace("```", ''))
                    test_cases.append(tests)
                    compiled_filenames.append(
                        os.path.join(f"{csv_path[:-4]}/{benchmark_name}.ts")
                    )

    # Batch test all outputs
    batch_results = batch_compile_typescript_to_file(
        compiled_filenames, programs_to_test, test_cases)
    print(batch_results)
    return len(batch_results)


def update_function_names(csv_path):
    df = pd.read_csv(csv_path)
    updated = False

    for idx, row in df.iterrows():
        benchmark_name = row['benchmark_name']
        output = row['output']
        compiled = row['did_compile']

        func_name_path = os.path.join(
            MY_ROOT_DIR + "rewriting-program-spaces/experiments/typescript/benchmarks/mbpp_benchmarks/",
            benchmark_name, 'func_name.txt'
        )
        if not os.path.exists(func_name_path):
            continue

        with open(func_name_path, 'r', encoding='utf-8') as f:
            func_name = f.read().strip()
        matches = list(re.finditer(r'\nfunction\s+([A-Za-z_][A-Za-z0-9_]*)', output))
        if len(matches) == 1 and compiled:
            old_name = matches[0].group(1)
            if old_name != func_name:
                new_output = re.sub(
                    re.escape(old_name),
                    func_name,
                    output
                )
                df.at[idx, 'output'] = new_output
                updated = True
        if len(matches) > 1 and compiled:
            old_name = matches[0].group(1)
            if old_name != func_name:
                print(csv_path, benchmark_name)

    if updated:
        df.to_csv(csv_path, index=False)


def process_test_scripts(folder_name: str) -> int:
    # Get the list of all .js files in the folder
    compiled_filenames = []

    # Iterate through all .js files in the folder
    for filename in os.listdir(folder_name):
        if filename.endswith('.js'):
            js_path = os.path.join(folder_name, filename)
            compiled_filenames.append(js_path)

    # Batch test all outputs
    try:
        batch_results = func_timeout(
            3600, test_javascript_batch, args=(compiled_filenames,)
        )
    except FunctionTimedOut:
        batch_results = [False] * len(compiled_filenames)

    # Write test results for all compiled programs in the file.
    with open(os.path.join(folder_name, 'test_results.txt'), 'w') as f:
        f.write(f"{batch_results}")
    return sum(batch_results)


# # # FUNCTIONS TO CLEAN AND ANALYZE EXPERIMENTAL OUTPUT # # #
# Run this to rename all mis-named functions in the csv files.
# Functions which cannot be resolved are printed out and must be resolved manually.
def rename_all():
    for temp in ['0.01', '0.3', '0.5', '0.7', '1.0']:
        for mode in ['GCD', 'TypedCD', "Unconstrained"]:
            for model in ['llama13b', 'deepseek-coder']:
                update_function_names(
                    MY_ROOT_DIR + f'rewriting-program-spaces/experiments/typescript/results2/{mode}_temp_{temp}_model_{model}.csv'
                )


# Compile all code + tests to .js files.
def compile_all():
    results = dict()

    for temp in ['0.01', '0.3', '0.5', '0.7', '1.0']:
        for mode in ['GCD', 'TypedCD', "Unconstrained"]:
            for model in ['llama13b', 'deepseek-coder']:
                results[(temp, mode, model)] = compile_csv(
                    MY_ROOT_DIR + f'rewriting-program-spaces/experiments/typescript/results2/{mode}_temp_{temp}_model_{model}.csv')
                print(f"{temp}_{mode}_{model} =>{results[(temp, mode, model)]}")


# Run the .js files to see what tests pass/fail.
def test_all():
    results = dict()

    for temp in ['0.01', '0.3', '0.5', '0.7', '1.0']:
        for mode in ['GCD', 'TypedCD', "Unconstrained"]:
            for model in ['llama13b', 'deepseek-coder']:
                results[(temp, mode, model)] = process_test_scripts(
                    MY_ROOT_DIR + f'rewriting-program-spaces/experiments/typescript/results2/{mode}_temp_{temp}_model_{model}/'
                )
                print(f"{temp}_{mode}_{model} =>{results[(temp, mode, model)]}")

    print(results)


if __name__ == "__main__":
    rename_all()
    # compile_all()
    # test_all()
