import pandas as pd
from pathlib import Path

def main(results_dir: Path = Path('.')):
    # find all csv result files
    csv_files = list(results_dir.glob('*.csv'))
    if not csv_files:
        print(f'No CSV files found in {results_dir.resolve()}')
        return

    # mapping checker_type to column labels
    checker_map = {
        'unconstrained': 'Unconstr.',
        'gcd': 'Syntax',
        'constrained': 'Semantics'
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

    models = table_df['model'].unique()
    temps = sorted(table_df['temperature'].unique())
    col_order = ['Unconstr.', 'Syntax', 'Semantics']

    print('\\begin{table}[h]')
    print('\\centering')
    print('\\caption{Performance of Different Decoding Strategies Across Models and Temperatures (Higher is Better). Best results per row are \\textbf{bolded}.}')
    print('\\label{tab:decoding-performance}')
    print('\\begin{tabular}{@{}l ccc ccc@{}}')
    print('\\toprule')
    # header
    print('\\multirow{2}{*}{\\textbf{Model & Temperature}}'
          ' & \\multicolumn{3}{c}{\\textbf{Without Codeblock}}'
          ' & \\multicolumn{3}{c}{\\textbf{With Codeblock}} \\\\')
    print('\\cmidrule(lr){2-4} \\cmidrule(lr){5-7}')
    print(' & \\textbf{Unconstr.} & \\textbf{Syntax} & \\textbf{Semantics}'
          ' & \\textbf{Unconstr.} & \\textbf{Syntax} & \\textbf{Semantics} \\\\')
    print('\\midrule')

    for model in models:
        print(f'\\textbf{{{model}}} \\\\')
        for temp in temps:
            cells = []
            for cb in [False, True]:
                for checker in col_order:
                    sub = table_df[
                        (table_df['model'] == model) &
                        (table_df['codeblock'] == cb) &
                        (table_df['temperature'] == temp) &
                        (table_df['checker'] == checker)
                    ]
                    if sub.empty:
                        raise ValueError(f"Missing data for {model}, codeblock={cb}, {checker}, T={temp}")
                    s = int(sub['success'].iloc[0])
                    t = int(sub['total'].iloc[0])
                    cells.append(f'{s}/{t}')
            print('T={:.2f} & '.format(temp) + ' & '.join(cells) + ' \\\\')
        print('\\midrule')
        total_cells = []
        for cb in [False, True]:
            for checker in col_order:
                sub_tot = totals_df[
                    (totals_df['model'] == model) &
                    (totals_df['codeblock'] == cb) &
                    (totals_df['checker'] == checker)
                ]
                if sub_tot.empty:
                    raise ValueError(f"Missing totals for {model}, codeblock={cb}, {checker}")
                s_all = int(sub_tot['success_all'].iloc[0])
                t_all = int(sub_tot['total_all'].iloc[0])
                total_cells.append(f'{s_all}/{t_all}')
        print('Total & ' + ' & '.join(total_cells) + ' \\\\')
    print('\\bottomrule')
    print('\\end{tabular}')
    print('\\end{table}')

if __name__ == '__main__':
    main()