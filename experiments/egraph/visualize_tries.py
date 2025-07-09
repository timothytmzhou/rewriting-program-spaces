import pandas as pd
import matplotlib.pyplot as plt
from pathlib import Path
import ast
import numpy as np

def main(results_dir: Path = Path('.')):
    # Set global font size for the plots.
    plt.rcParams.update({'font.size': 16})
    
    # Find all CSV files without codeblock
    csv_files = [f for f in results_dir.glob('*.csv') 
                 if 'codeblock' not in f.stem and f.stem.count('-') >= 1]
    
    if not csv_files:
        print(f'No CSV files found in {results_dir.resolve()}')
        return

    all_data = []
    
    for csv_file in csv_files:
        # Parse filename: model-checker
        name = csv_file.stem
        parts = name.split('-')
        model = parts[0]
        checker = parts[-1]
        
        df_csv = pd.read_csv(csv_file)
        
        for _, row in df_csv.iterrows():
            temp = float(row['temperature'])
            
            # Parse tries_per_token: Counter({(tries, freq): ...})
            tries_str = row['tries_per_token']
            tries_dict = ast.literal_eval(tries_str.replace('Counter(', '').rstrip(')'))
            
            # Extract (tries, freq) pairs
            for (tries, freq), _ in tries_dict.items():
                all_data.append({
                    'model': model,
                    'checker': checker, 
                    'temperature': temp,
                    'tries': tries,
                    'frequency': freq
                })
    
    df = pd.DataFrame(all_data)
    
    # Remove data for unconstrained checker
    df = df[df['checker'] != 'unconstrained']
    
    # Get unique models and checkers for aggregation.
    models = sorted(df['model'].unique())
    checkers = sorted(df['checker'].unique())

    # Mapping for legend labels.
    legend_mapping = {
        'constrained': 'Semantics',
        'gcd': 'Syntax'
    }
    colors = ['#1f77b4','#ff7f0e']  # blue and orange
    
    # Create one figure per model.
    for model in models:
        subset_model = df[df['model'] == model]
        # Pivot the data so that each checker becomes a column, indexed by tries.
        pivot = subset_model.pivot_table(index='tries',
                                         columns='checker', 
                                         values='frequency', 
                                         aggfunc='sum',
                                         fill_value=0)
        # Ensure the tries are sorted.
        pivot = pivot.sort_index()
        x_ticks = pivot.index.values

        plt.figure(figsize=(6, 4))
        bottom = np.zeros(len(x_ticks))
        
        # Iterate over checkers in the sorted order.
        for i, checker in enumerate(checkers):
            if checker in pivot.columns:
                freqs = pivot[checker].values
                label = legend_mapping.get(checker, checker)
                plt.bar(x_ticks, freqs, bottom=bottom, width=.9, 
                        alpha=.8, label=label, color=colors[i % len(colors)])
                bottom += freqs  # update bottom for stacking

        plt.xlabel('Number of Tokens Guessed', fontsize=16)
        plt.ylabel('Frequency', fontsize=16)
        if model == "deepseek":
            plt.title('DeepSeek-6.7B', fontsize=18)
        elif model == "llama7b":
            plt.title('CodeLlama-7B', fontsize=18)
        elif model == "llama13b":
            plt.title('CodeLlama-13B', fontsize=18)
        else:
            # For other models, use the model name directly.
            plt.title(f'{model}', fontsize=18)
        plt.legend()
        plt.yscale('log')
        plt.xlim(0, 125)  # Set x-axis to max out at 125.
        plt.tight_layout()
        # Save figure with model name in file name.
        plt.savefig(f'tries_per_token_viz_{model}.png', dpi=300, bbox_inches='tight')
        plt.show()

if __name__ == '__main__':
    main()
