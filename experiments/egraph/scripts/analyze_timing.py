import pandas as pd
import argparse
from pathlib import Path
from tabulate import tabulate

def main(results_dir: Path = Path('.')):
    # find all csv result files  
    csv_files = list(results_dir.glob('*-constrained.csv'))
    if not csv_files:
        print(f'No constrained CSV files found in {results_dir.resolve()}')
        return

    records = []
    for csv_file in csv_files:
        name = csv_file.stem
        parts = name.split('-')
        # parse filename: model[-codeblock]-constrained
        if parts[-1] == 'constrained':
            codeblock = 'codeblock' in parts[:-1]
            model = parts[0]
        else:
            continue

        df = pd.read_csv(csv_file)
        df['temperature'] = df['temperature'].astype(float)
        temps = sorted(df['temperature'].unique())
        
        total_per_temp = df.groupby('temperature')['total_realizability_time'].sum()
        tokens_per_temp = df.groupby('temperature')['num_tokens_generated'].sum()
        total_all_time = total_per_temp.sum()
        total_all_tokens = tokens_per_temp.sum()
        
        for temp in temps:
            total_time = total_per_temp.get(temp, 0)
            total_tokens = tokens_per_temp.get(temp, 0)
            
            # Calculate time per token in milliseconds
            time_per_token_ms = (total_time / total_tokens * 1000) if total_tokens > 0 else 0
            
            records.append({
                'model': model,
                'codeblock': codeblock,
                'temperature': temp,
                'time_per_token_ms': time_per_token_ms,
                'total_all_time': total_all_time,
                'total_all_tokens': total_all_tokens
            })

    table_df = pd.DataFrame(records)
    totals_df = (
        table_df
        .groupby(['model', 'codeblock'], as_index=False)
        .agg({'total_all_time': 'max', 'total_all_tokens': 'max'})
    )

    models = ["deepseek", "llama7b", "llama13b"]
    temps = sorted(table_df['temperature'].unique())

    def create_table(codeblock_value, table_name):
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
                    (table_df['codeblock'] == codeblock_value) &
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

    create_table(False, "No Delimit")
    create_table(True, "Delimit")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Analyze timing performance from CSV files')
    parser.add_argument('results_dir', type=Path, help='Directory containing CSV result files')
    args = parser.parse_args()
    
    main(args.results_dir)
