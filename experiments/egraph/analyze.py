import pandas as pd
import glob
import os
from collections import defaultdict

def analyze_results():
    # Get all CSV files in the current directory
    csv_files = glob.glob("results/*.csv")
    
    # Initialize data structure to store results for each checker type
    results = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    
    # Define the temperatures we expect
    temperatures = [0.01, 0.3, 0.5, 0.7, 1.0]
    checker_types = ['constrained', 'unconstrained', 'gcd']
    
    # Process each CSV file
    for file in csv_files:
        # Skip if it doesn't contain a checker type
        if not any(checker in file for checker in checker_types):
            continue
            
        # Extract model name and codeblock status from filename
        basename = os.path.basename(file).replace('.csv', '')
        
        # Determine if it's a codeblock experiment
        is_codeblock = 'codeblock' in basename
        
        # Extract model name and checker type
        model_name = basename
        current_checker = None
        for checker in checker_types:
            if model_name.endswith(f'-{checker}'):
                current_checker = checker
                model_name = model_name[:-len(f'-{checker}')]
                break
        
        if current_checker is None:
            continue
            
        if is_codeblock:
            model_name = model_name.replace('-codeblock', '')
        
        # Read the CSV file
        try:
            df = pd.read_csv(file)
            
            # Group by temperature and calculate success rates
            success_by_temp = df.groupby('temperature')['success'].sum()
            
            # Store results
            codeblock_key = 'with_codeblock' if is_codeblock else 'without_codeblock'
            
            for temp in temperatures:
                if temp in success_by_temp:
                    results[current_checker][model_name][codeblock_key][temp] = success_by_temp[temp]
                else:
                    results[current_checker][model_name][codeblock_key][temp] = 0
                    
        except Exception as e:
            print(f"Error reading {file}: {e}")
    
    # Generate LaTeX tables for each checker type
    for checker_type in checker_types:
        print(f"\n%=====================================")
        print("\\begin{table}[h]")
        print("\\centering")
        print(f"\\caption{{{checker_type.upper()} Performance Analysis}}")
        print("\\begin{tabular}{@{} l")
        print("                 *{6}{c}")
        print("                 *{6}{c} @{}}")
        print("\\toprule")
        print("  & \\multicolumn{6}{c}{Without Codeblock}")
        print("  & \\multicolumn{6}{c}{With Codeblock} \\\\")
        print("\\cmidrule(lr){2-7} \\cmidrule(lr){8-13}")
        print("  & \\multicolumn{6}{c}{Temperature}")
        print("  & \\multicolumn{6}{c}{Temperature} \\\\")
        print("\\cmidrule(lr){2-7} \\cmidrule(lr){8-13}")
        print("Model")
        print("  & 0.01 & 0.3  & 0.5  & 0.7  & 1.0  & Total")
        print("  & 0.01 & 0.3  & 0.5  & 0.7  & 1.0  & Total \\\\")
        print("\\midrule")
        
        # Generate rows for each model
        for model_name in sorted(results[checker_type].keys()):
            # Escape underscores in model names for LaTeX
            latex_model_name = model_name.replace('_', '\\_')
            print(latex_model_name)
            
            # Without codeblock row
            without_total = 0
            without_parts = []
            for temp in temperatures:
                successes = results[checker_type][model_name]['without_codeblock'].get(temp, 0)
                without_total += successes
                without_parts.append(f"{successes}/10")
            print("  & " + " & ".join(f"{v:>5}" for v in without_parts) + f" & {without_total}/50")
            
            # With codeblock row
            with_total = 0
            with_parts = []
            for temp in temperatures:
                successes = results[checker_type][model_name]['with_codeblock'].get(temp, 0)
                with_total += successes
                with_parts.append(f"{successes}/10")
            print("  & " + " & ".join(f"{v:>5}" for v in with_parts) + f" & {with_total}/50 \\\\")
            
        print("\\bottomrule")
        print("\\end{tabular}")
        print("\\end{table}")
        print()
        
        # Also save as CSV for further analysis
        output_data = []
        for model_name in sorted(results[checker_type].keys()):
            row_data = {'Model': model_name}
            
            # Without codeblock data
            without_total = 0
            for temp in temperatures:
                successes = results[checker_type][model_name]['without_codeblock'].get(temp, 0)
                without_total += successes
                row_data[f'Without_T{temp}'] = f"{successes}/10"
            row_data['Without_Total'] = f"{without_total}/50"
            
            # With codeblock data
            with_total = 0
            for temp in temperatures:
                successes = results[checker_type][model_name]['with_codeblock'].get(temp, 0)
                with_total += successes
                row_data[f'With_T{temp}'] = f"{successes}/10"
            row_data['With_Total'] = f"{with_total}/50"
            
            output_data.append(row_data)
        
        # Save summary table
        if output_data:
            summary_df = pd.DataFrame(output_data)
            summary_df.to_csv(f'model_performance_summary_{checker_type}.csv', index=False)
        else:
            print(f"No data found for {checker_type}")
        print()

if __name__ == "__main__":
    analyze_results()