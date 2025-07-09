import pandas as pd
from pathlib import Path

def main(results_dir: Path = Path('.')):
    # find all csv result files for constrained checker without codeblock
    csv_files = [f for f in results_dir.glob('*-constrained.csv') if 'codeblock' not in f.stem]
    if not csv_files:
        print(f'No constrained CSV files found in {results_dir.resolve()}')
        return

    records = []
    for csv_file in csv_files:
        name = csv_file.stem
        parts = name.split('-')
        # parse filename: model-constrained
        model = parts[0]

        df = pd.read_csv(csv_file)
        df['temperature'] = df['temperature'].astype(float)
        temps = sorted(df['temperature'].unique())
        
        for temp in temps:
            temp_df = df[df['temperature'] == temp]
            total_realiz_time = temp_df['total_realizability_time'].sum()
            total_tokens = temp_df['num_tokens_generated'].sum()
            
            # Calculate time per token in milliseconds
            time_per_token_ms = (total_realiz_time / total_tokens * 1000) if total_tokens > 0 else 0
            
            records.append({
                'model': model,
                'temperature': temp,
                'total_realizability_time': total_realiz_time,
                'time_per_token_ms': time_per_token_ms
            })

    table_df = pd.DataFrame(records)
    models = table_df['model'].unique()
    temps = sorted(table_df['temperature'].unique())

    print('\\begin{table}[h]')
    print('\\centering')
    print('\\caption{Realizability Checking Time for Constrained Decoding (Without Codeblock)}')
    print('\\label{tab:realizability-timing}')
    print('\\begin{tabular}{@{}l cc@{}}')
    print('\\toprule')
    print('\\textbf{Model & Temperature} & \\textbf{Total Time (s)} & \\textbf{Time per Token (ms)} \\\\')
    print('\\midrule')

    for model in models:
        print(f'\\textbf{{{model}}} \\\\')
        for temp in temps:
            row = table_df[
                (table_df['model'] == model) &
                (table_df['temperature'] == temp)
            ]
            if row.empty:
                raise ValueError(f"Missing data for {model}, T={temp}")
            
            total_time = row['total_realizability_time'].iloc[0]
            time_per_token = row['time_per_token_ms'].iloc[0]
            
            print(f'T={temp:.2f} & {total_time:.2f} & {time_per_token:.2f} \\\\')
        
        if model != models[-1]:  # Don't add midrule after last model
            print('\\midrule')
    
    print('\\bottomrule')
    print('\\end{tabular}')
    print('\\end{table}')

if __name__ == '__main__':
    main()