# Claims
Claim 1: Across nearly all configurations, semantic constrained decoding delivers consistent and often dramatic improvements (Table 1). 

Claim 2: Overhead on decoding time range from tens to a few hundred milliseconds per token. (Table 2)

Claim 3: In general, even with semantic constrained decoding the first token tried is accepted most of the time. (Figure 6)

TODO: more specific claims about typescript performance?

# Installation


# Evaluation Instructions

This section explains how to reproduce the results presented in the paper, including both (1) regenerating tables and figures from the provided raw data and (2) generating new data by re-running experiments. Since (2) requires GPU access and can take a long time (several days), you can also specify a subset of the experiments to run. With (2), there is some inherent nondeterminism from running LMs---the generated data should be similar but may not be exactly the same.

## Reproducing Tables and Figures from Provided Raw Data
The raw data for our experiments is in `experiments/egraph/paper_data` and `experiments/typescript/paper_data` respectively. To get the tables and figures shown in the paper, run the following commands:

### EGraph Benchmarks
Table 1:
```bash
python -m experiments.egraph.scripts.analyze_success experiments/egraph/paper_data
```
Note: in the paper, there was a typographic error and the `deepseek, constrained, delimit, T=.5` entry is off by one in the paper (same for the total for that row).

Table 2:
```bash
python -m experiments.egraph.scripts.analyze_timing experiments/egraph/paper_data
```


Figure 6:
```bash
python -m experiments.egraph.scripts.visualize_tries experiments/egraph/paper_data
```
This will save the histograms for every model as `.png` files. You can pass the `--output-dir` flag to specify the path where the images are saved (root by default).


### TypeScript Benchmarks

## Reproducing Raw Data (Requires GPUs)
### EGraph Benchmarks
The following command will run ALL egraph experiments:
```bash
python -m experiments.egraph.scripts.run
```
This may take a long time, so instead the reviewer may want to only run on a subset of the experiments. To do this, pass in additional arguments specifying which experiments to run. For example,
```bash
python -m experiments.egraph.scripts.run --models llama7b --temps 0.01
```
will run only experiments using llama7b at temperature .01. 
The options for the script are listed below.
```bash
options:
  -h, --help            show this help message and exit
  --models {llama13b,llama7b,deepseek} [{llama13b,llama7b,deepseek} ...]
                        Which models to run (default: all).
  --temps {0.01,0.3,0.5,0.7,1.0} [{0.01,0.3,0.5,0.7,1.0} ...]
                        Which temperatures to run (default: all).
  --delimit DELIMIT     Run with delimiters: yes, no, or both (default: both).
  --checkers {constrained,unconstrained,gcd} [{constrained,unconstrained,gcd} ...]
                        Which checker types to run (default: all).
  --output OUTPUT       Path to the output directory (default: experiments/egraph/data).
```

Once the output is generated, tables can be produced using the same procedure as with the raw data, just with the input directory changed to where the results were stored.

### TypeScriot Benchmarks

# Additional Description
