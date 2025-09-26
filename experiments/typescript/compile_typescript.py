import concurrent.futures
import subprocess
import tempfile
import os

# # # GPT generated code below


def compile_typescript(ts_code: str) -> bool:
    # Create a temporary file to store the TypeScript code
    with tempfile.NamedTemporaryFile(delete=False, suffix='.ts') as temp_file:
        # Write the TypeScript code to the temp file
        temp_file.write(ts_code.encode('utf-8'))
        temp_file_path = temp_file.name

    try:
        # Run the TypeScript compiler (tsc) on the temp file
        result = subprocess.run(
            ['tsc', '--target', 'es2016', '--module', 'commonjs', temp_file_path],
            capture_output=True, text=True
        )

        # Check if there were compilation errors
        return result.returncode == 0
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)


def batch_compile_typescript_to_file(
    filenames: list[str], ts_code_list: list[str], ts_tests_list: list[str]
) -> list[str]:
    # Write TypeScript code and tests to files if they don't exist
    for filename, ts_code, ts_tests in zip(filenames, ts_code_list, ts_tests_list):
        if not os.path.exists(filename):
            with open(filename, "w") as f:
                f.write(ts_code)
                f.write("\n")
                f.write(ts_tests)

    # Compile each TypeScript file separately in parallel.
    # Skip if the code has already been compiled.
    def compile_ts(ts_path):
        js_path = ts_path[:-3] + ".js"
        if os.path.exists(js_path):
            return True
        try:
            compile_result = subprocess.run(
                ["tsc", "--target", "es2016", "--module", "commonjs", ts_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            return compile_result.returncode == 0
        except Exception as e:
            print(
                "Error compiling TypeScript file: ", ts_path,
                "\nwith error: ", e
            )
            return False

    with concurrent.futures.ThreadPoolExecutor() as executor:
        compile_results = list(executor.map(compile_ts, filenames))

    # remove ts files
    for filename in filenames:
        if os.path.exists(filename):
            os.remove(filename)
    return [fn for fn, success in zip(filenames, compile_results) if success]


def test_javascript_batch(js_filenames: list[str]) -> list[bool]:
    results = []

    # Run each compiled JavaScript file and collect results
    def run_js(js_path):
        try:
            run_result = subprocess.run(
                ["node", js_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=60
            )
            return run_result.returncode == 0
        except Exception as e:
            print(
                "Error running TypeScript test: ", js_path,
                "\nwith error: ", e
            )
            return False

    with concurrent.futures.ThreadPoolExecutor() as executor:
        results = list(executor.map(run_js, js_filenames))

    return results
