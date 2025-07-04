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
        result = subprocess.run(['tsc', '--target', 'es2016', temp_file_path],
                                capture_output=True, text=True)

        # Check if there were compilation errors
        return result.returncode == 0
    finally:
        # Clean up the temporary file
        if os.path.exists(temp_file_path):
            os.remove(temp_file_path)
