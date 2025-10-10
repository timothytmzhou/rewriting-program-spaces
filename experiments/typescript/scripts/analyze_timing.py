import argparse
import pandas as pd
from pathlib import Path
from tabulate import tabulate


def main(results_dir: Path = Path('results')):
    # find all csv result files using typepruner
    csv_files = list(results_dir.glob('TypedCD*.csv'))
    if not csv_files:
        print(f'No typeruning CSV files found in {results_dir.resolve()}')
        return

    records = []
    for csv_file in csv_files:
        name = csv_file.stem
        parts = name.split('_')
        # parse filename: model-constrained
        model = parts[-1]

        df = pd.read_csv(csv_file)
        df['temperature'] = df['temperature'].astype(float)
        temps = sorted(df['temperature'].unique())

        for temp in temps:
            temp_df = df[df['temperature'] == temp]
            total_realiz_time = temp_df['total_realizability_time'].sum()
            avg_realiz_time = total_realiz_time / \
                temp_df['total_realizability_time'].count()
            total_tokens = temp_df['num_tokens_generated'].sum()

            # Calculate time per token in milliseconds
            time_per_token_ms = (
                total_realiz_time / total_tokens * 1000) if total_tokens > 0 else 0

            records.append({
                'model': model,
                'temperature': temp,
                'total_realizability_time': avg_realiz_time,
                'time_per_token_ms': time_per_token_ms
            })

    table_df = pd.DataFrame(records)
    models = ["deepseek", "llama7b", "llama13b"]
    temps = sorted(table_df['temperature'].unique())

    def create_table(table_name):
        # Create timing table for the given codeblock value
        data = []

        # Create model header row
        model_header = []
        for model in models:
            model_header.append(model)
            for _ in range(len(temps) - 1):
                model_header.append("")

        # Create temperature header row
        temp_header = []
        for model in models:
            for temp in temps:
                temp_header.append(f"T={temp}")

        # Create data row
        row = []
        for model in models:
            # Add temperature columns
            for temp in temps:
                sub = table_df[
                    (table_df['model'] == model) &
                    (table_df['temperature'] == temp)
                ]
                if not sub.empty:
                    time_per_token = round(sub['time_per_token_ms'].iloc[0])
                    row.append(f'{time_per_token}')
                else:
                    row.append('N/A')

        # Add headers as data rows and then the actual data
        data.append(model_header)
        data.append(temp_header)
        data.append(row)

        print(f"\n{table_name}")
        print(tabulate(data, tablefmt='grid'))

    create_table("Typescript Portion of Table 2")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Analyze timing performance from CSV files')
    parser.add_argument('results_dir', type=Path,
                        help='Directory containing CSV result files')
    args = parser.parse_args()

    main(args.results_dir)
