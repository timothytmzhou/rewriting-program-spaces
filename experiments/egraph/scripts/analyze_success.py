import pandas as pd
from pathlib import Path
import argparse
from tabulate import tabulate

def main(results_dir: Path):
    # find all csv result files
    csv_files = list(results_dir.glob('*.csv'))
    if not csv_files:
        print(f'No CSV files found in {results_dir.resolve()}')
        return

    # mapping checker_type to column labels
    checker_map = {
        'unconstrained': 'Unconstrained',
        'gcd': 'Grammar',
        'constrained': 'Semantic'
    }

    records = []
    for csv_file in csv_files:
        name = csv_file.stem
        parts = name.split('-')
        # parse filename: model[-codeblock]-checker
        if parts[-1] in checker_map:
            checker_key = parts[-1]
            codeblock = 'codeblock' in parts[:-1]
            model = parts[0]
        else:
            raise ValueError(f"Unexpected filename pattern: {name}")

        df = pd.read_csv(csv_file)
        df['temperature'] = df['temperature'].astype(float)
        temps = sorted(df['temperature'].unique())
        total_per_temp = df.groupby('temperature').size()
        success_per_temp = df[df['success']].groupby('temperature').size()
        total_all = int(total_per_temp.sum())
        success_all = int(success_per_temp.sum())

        for temp in temps:
            total = int(total_per_temp.get(temp, 0))
            success = int(success_per_temp.get(temp, 0))
            records.append({
                'model': model,
                'codeblock': codeblock,
                'checker': checker_map[checker_key],
                'temperature': temp,
                'success': success,
                'total': total,
                'success_all': success_all,
                'total_all': total_all
            })

    table_df = pd.DataFrame(records)
    totals_df = (
        table_df
        .groupby(['model', 'codeblock', 'checker'], as_index=False)
        .agg({'success_all': 'max', 'total_all': 'max'})
    )

    model_names = ["deepseek", "llama7b", "llama13b"]
    temps = [0.01, 0.3, 0.5, 0.7, 1.0]
    checkers = ['Unconstrained', 'Grammar', 'Semantic']

    def create_table(codeblock_value, table_name):
        # Create pivot table for the given codeblock value
        data = []
        for checker in checkers:
            row = [checker]
            for model_name in model_names:
                # Add temperature columns
                for temp in temps:
                    sub = table_df[
                        (table_df['model'] == model_name) &
                        (table_df['codeblock'] == codeblock_value) &
                        (table_df['checker'] == checker) &
                        (table_df['temperature'] == temp)
                    ]
                    if not sub.empty:
                        s = int(sub['success'].iloc[0])
                        t = int(sub['total'].iloc[0])
                        row.append(f'{s}')
                    else:
                        row.append('N/A')
                
                # Add total column
                sub_tot = totals_df[
                    (totals_df['model'] == model_name) &
                    (totals_df['codeblock'] == codeblock_value) &
                    (totals_df['checker'] == checker)
                ]
                if not sub_tot.empty:
                    s_all = int(sub_tot['success_all'].iloc[0])
                    t_all = int(sub_tot['total_all'].iloc[0])
                    row.append(f'{s_all}')
                else:
                    row.append('N/A')
            data.append(row)
        
        # Create headers
        headers = ['Checker']
        for model_name in model_names:
            for temp in temps:
                headers.append("")
            headers.append(f'{model_name}\nTotal')
        
        print(f"\n{table_name}")
        print(tabulate(data, headers=headers, tablefmt='grid'))

    create_table(False, "No Delimit")
    create_table(True, "Delimit")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze success rates from CSV files')
    parser.add_argument('results_dir', type=Path, help='Directory containing CSV result files')
    args = parser.parse_args()
    
    main(args.results_dir)
