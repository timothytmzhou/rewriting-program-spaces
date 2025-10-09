import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import ast
import argparse


def main(results_dir: Path, output_dir: Path):
    # Set global font size for the plots.
    plt.rcParams.update({'font.size': 16})
    
    # Find all CSV files without 'codeblock' in their stem and with at least one hyphen
    csv_files = [f for f in results_dir.glob('*.csv') 
                 if 'codeblock' in f.stem and f.stem.count('-') >= 1]
    
    if not csv_files:
        print(f'No CSV files found in {results_dir.resolve()}')
        return

    # Collect data from all CSVs into a list of dicts
    all_data = []
    for csv_file in csv_files:
        # Filename format: model-checker.csv
        model, checker = csv_file.stem.split('-')[0], csv_file.stem.split('-')[-1]
        df_csv = pd.read_csv(csv_file)
        for _, row in df_csv.iterrows():
            temp = float(row['temperature'])
            # Parse the Counter-like string into a dict of (tries, freq)
            tries_str = row['tries_per_token']
            tries_dict = ast.literal_eval(tries_str.replace('Counter(', '').rstrip(')'))
            for (tries, freq), _ in tries_dict.items():
                all_data.append({
                    'model': model,
                    'checker': checker,
                    'temperature': temp,
                    'tries': tries,
                    'frequency': freq
                })

    # Build DataFrame and remove unconstrained checker
    df = pd.DataFrame(all_data)
    df = df[df['checker'] != 'unconstrained']

    # Create buckets of size 5: 0-4 -> 0, 5-9 -> 5, etc.
    df['bucket'] = (df['tries'] // 5) * 5

    # Unique models and checkers
    models = sorted(df['model'].unique())
    checkers = sorted(df['checker'].unique())

    # Legend names and colors
    legend_mapping = {
        'constrained': 'Semantics',
        'gcd': 'Grammar'
    }
    colors = ['#ff7f0e', '#1f77b4']

    for model in models:
        subset = df[df['model'] == model]
        # Sum frequencies per bucket and checker
        grouped = subset.groupby(['bucket', 'checker'], as_index=False)['frequency'].sum()
        # Pivot so each checker is a column
        pivot = grouped.pivot_table(
            index='bucket',
            columns='checker',
            values='frequency',
            fill_value=0
        ).sort_index()

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
        plt.ylabel('Frequency', fontsize=14)
        plt.xlim(-0.5, 125)  # adjust to include the first and last groups


        plt.yscale('log')
        plt.legend()
        plt.tight_layout()
        plt.savefig(output_dir / f'equiv_tries_{model}.png', dpi=300, bbox_inches='tight')
        plt.show()

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Visualize tries per token from CSV files')
    parser.add_argument('data_dir', type=Path, help='Directory containing CSV files')
    parser.add_argument('--output_dir', default=Path("."), type=Path, help='Directory to create graphs files') 
    args = parser.parse_args()   
    main(args.data_dir, args.output_dir)
