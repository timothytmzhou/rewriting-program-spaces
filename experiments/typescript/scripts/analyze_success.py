import argparse
from collections import defaultdict
from pathlib import Path
import pandas as pd
from tabulate import tabulate


def analyze_results(results_dir: Path):
    # find all csv result files
    csv_files = list(results_dir.glob('*.csv'))
    if not csv_files:
        print(f'No CSV files found in {results_dir.resolve()}')
        return

    # Initialize data structure to store results for each checker type
    successes: dict[tuple[str, str, str], int] = defaultdict(lambda: 0)
    totals: dict[tuple[str, str, str], int] = defaultdict(lambda: 0)

    # Define the checkers, models, and temperatures we expect
    checkers = ['Unconstrained', 'GCD', 'TypedCD']
    models = ['deepseek', 'llama7b', 'llama13b']
    temps = ['0.01', '0.3', '0.5', '0.7', '1.0']

    # Process each CSV file
    for csv_file in csv_files:
        # Extract base file name
        basename = csv_file.stem

        # Extract model, temp, and checker names
        try:
            parts = basename.split('_')
            checker = parts[0]
            assert checker in checkers
            temp = parts[2]
            assert temp in temps
            model = parts[-1]
            assert model in models
        except Exception:
            raise ValueError(f"Unexpected csv filename pattern: {basename}")

        # Read the CSV file
        try:
            df = pd.read_csv(csv_file)

            # Store results
            totals[(checker, model, temp)] = df.shape[0]
            successes[(checker, model, temp)] = df['did_compile'].sum()

        except Exception as e:
            print(f"Error reading {csv_file}: {e}")

    def create_table(table_name):
        # Create pivot table for the given codeblock value
        data = []
        for checker in checkers:
            row = [checker]
            for model in models:
                # Add temperature columns
                success_sum = 0
                total_sum = 0
                for temp in temps:
                    s = successes[(checker, model, temp)]
                    t = totals[(checker, model, temp)]
                    success_sum += s
                    total_sum += t
                    if t != 0:
                        row.append(f'{s}')
                    else:
                        row.append('N/A')

                # Add total column
                if total_sum != 0:
                    row.append(f'{success_sum}')
                else:
                    row.append('N/A')
            data.append(row)

        # Create headers
        headers = ['Checker']
        for model in models:
            for temp in temps:
                headers.append("")
            headers.append(f'{model}\nTotal')

        print(f"\n{table_name}")
        print(tabulate(data, headers=headers, tablefmt='grid'))

    create_table("Typescript Portion of Table 1")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Analyze success rates from CSV files')
    parser.add_argument('results_dir', type=Path,
                        help='Directory containing CSV result files')
    args = parser.parse_args()

    analyze_results(args.results_dir)
