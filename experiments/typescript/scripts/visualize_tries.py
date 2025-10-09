import argparse
import ast
import matplotlib.pyplot as plt
import pandas as pd
from pathlib import Path

SUCCEEDED_IN_ONE_RUN = 0
SUCCEEDED_AFTER_MORE_THAN_25 = 0
TOTAL_TOKENS = 0


def main(data_dir: Path, output_dir: Path):
    global TOTAL_TOKENS
    global SUCCEEDED_IN_ONE_RUN
    global SUCCEEDED_AFTER_MORE_THAN_25
    # Set global font size for the plots.
    plt.rcParams.update({'font.size': 16})

    # Find all CSV files without codeblock
    csv_files = [f for f in data_dir.glob('*.csv')]

    if not csv_files:
        print(f'No CSV files found in {data_dir.resolve()}')
        return

    all_data = []

    for csv_file in csv_files:
        # Parse filename: model-checker
        name = csv_file.stem
        parts = name.split('_')
        model = parts[-1]
        checker = parts[0]

        df_csv = pd.read_csv(csv_file)

        for _, row in df_csv.iterrows():
            temp = float(row['temperature'])

            # Parse tries_per_token: Counter({(tries, freq): ...})
            tries_str = row['tries_per_token']
            tries_dict = ast.literal_eval(
                tries_str.replace('Counter(', '').rstrip(')'))

            # Extract (tries, freq) pairs
            for (tries, freq), _ in tries_dict.items():
                all_data.append({
                    'model': model,
                    'checker': checker,
                    'temperature': temp,
                    'tries': tries,
                    'frequency': freq,
                    'benchmark': row['benchmark_name'],
                    'execution_time': row['execution_time'],
                    'num_tokens_generated': row['num_tokens_generated']
                })

    df = pd.DataFrame(all_data)

    # Remove data for unconstrained checker
    df = df[df['checker'] != 'Unconstrained']

    # Create buckets of size 5: 0-4 -> 0, 5-9 -> 5, etc.
    df['bucket'] = (df['tries'] // 5) * 5

    # Get unique models and checkers for aggregation.
    models = sorted(df['model'].unique())
    checkers = sorted(df['checker'].unique())
    checkers.reverse()

    # Mapping for legend labels.
    legend_mapping = {
        'TypedCD': 'Semantics',
        'GCD': 'Grammar'
    }
    colors = ['#ff7f0e', '#1f77b4',]  # blue and orange

    # Create one figure per model.
    for model in models:
        subset = df[df['model'] == model]
        # Sum frequencies per bucket and checker
        grouped = subset.groupby(['bucket', 'checker'], as_index=False)[
            'frequency'].sum()
        # Pivot the data so that each checker becomes a column, indexed by tries.
        pivot = grouped.pivot_table(index='bucket',
                                    columns='checker',
                                    values='frequency',
                                    fill_value=0)
        # Ensure the tries are sorted.
        pivot = pivot.sort_index()
        buckets = pivot.index.values
        num_checkers = len(checkers)
        bar_width = 5 * 0.9 / num_checkers

        plt.figure(figsize=(6, 4))
        # Draw bars
        for i, checker in enumerate(checkers):
            if checker in pivot.columns:
                freqs = pivot[checker].values
                offsets = buckets - 0.45 + i * bar_width + bar_width / 2
                label = legend_mapping.get(checker, checker)
                plt.bar(offsets, freqs,
                        width=bar_width,
                        alpha=0.8,
                        label=label,
                        color=colors[i % len(colors)])

        # Labels and ticks
        plt.title(f'Number of Tokens Tried Per Success', fontsize=16)
        plt.xlabel('Number of Tokens Tried', fontsize=14)
        plt.ylabel('Frequency', fontsize=14)
        plt.xlim(-0.5, 125)  # adjust to include the first and last groups

        plt.yscale('log')
        plt.legend()
        plt.tight_layout()
        output_file = output_dir / f'typescript_tries_{model}.png'
        plt.savefig(output_file, dpi=300, bbox_inches='tight')
        plt.show()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze realizability checks from CSV files (Fig 6b)')
    parser.add_argument('data_dir', type=Path, help='Directory containing CSV files')
    parser.add_argument('--output_dir', default=Path("."), type=Path, help='Directory to create graphs files')
    args = parser.parse_args()

    main(args.data_dir, args.output_dir)
