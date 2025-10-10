# Claims
Claim 1: Across nearly all configurations, semantic constrained decoding delivers consistent and often dramatic improvements (Table 1). 

Claim 2: Overhead on decoding time ranges from tens to a few hundred milliseconds per token. (Table 2)

Claim 3: In general, even with semantic constrained decoding the first token tried is accepted most of the time. (Figure 6)

# Installation
TODO: Write installation instructions.
Switch directories (IMPORTANT: run all commands from the `chopchop` directory).
```bash
cd chopchop
```
As a sanity check, you can run:
```bash
python -m pytest
```
The tests should take 1-2 minutes to pass.


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
Table 1:
From the `rewriting-program-spaces` directory, run
```bash
python -m experiments.typescript.scripts.analyze_success experiments/typescript/paper_data
```

Table 2:
From the `rewriting-program-spaces` directory, run
```bash
python -m experiments.typescript.scripts.analyze_timing experiments/typescript/paper_data
```


Figure 6:
From the `rewriting-program-spaces` directory, run
```bash
python -m experiments.typescript.scripts.visualize_tries experiments/typescript/paper_data
```
This will save the histograms for every model as `.png` files.
Figure 6 shows the histogram for llama7b specifically.
You can pass the `--output-dir` flag to specify the path where the images are saved (the current working directory by default).


## Reproducing Raw Data
The largest model, llama-13b, requires ~30 GB of VRAM.
The smallest model, deepseek-coder, requires ~15GB of VRAM.
Because LLMs are inherently stochastic, data may differ from what is reported in the paper, but trends should be preserved. 
### EGraph Benchmarks
The following command will run ALL egraph experiments:
```bash
python -m experiments.egraph.scripts.run
```
This may take a long time, so instead the reviewer may want to only run on a subset of the experiments. 
To do this, pass in additional arguments specifying which experiments to run.
Experiments are split along several dimensions (models, temperature, checker type, etc.).
Multiple values can be specified per dimension (e.g. to run with temperatures .01 AND .3).
If a dimension is not specified, the script will default to using all values.
For example,
```bash
python -m experiments.egraph.scripts.run --models llama7b --temps 0.01 .3
```
will run only experiments using llama7b at temperatures .01 and .3. 
The options for the script are listed below.
```bash
Run egraph experiments.

options:
  -h, --help            show this help message and exit
  --models {llama13b,llama7b,deepseek} [{llama13b,llama7b,deepseek} ...]
                        Which models to run (default: all).
  --temps {0.01,0.3,0.5,0.7,1.0} [{0.01,0.3,0.5,0.7,1.0} ...]
                        Which temperatures to run (default: all).
  --delimit DELIMIT     Run with delimiters: yes, no, or both (default: both).
  --checkers {semantic,unconstrained,grammar} [{semantic,unconstrained,grammar} ...]
                        Which checker types to run (default: all).
  --output OUTPUT       Path to the output directory (default: experiments/egraph/data).
```

Once the output is generated, tables can be produced using the same procedure as with the raw data, just with the input directory changed to where the results were stored.

### TypeScript Benchmarks
The following command will run ALL typescript experiments (expect this to take 2-3 days):
```bash
python -m experiments.typescript.scripts.run
```
As above, if this will take too long it is possible to only specify a subset of the experiments to run.
For example,
```bash
python -m experiments.typescript.scripts.run --models llama7b --temps 0.01 0.3 
```
will run only the 6 experiments using llama7b at temperatures .01 and 0.3.
The options for the script are listed below.
```bash
Run typescript experiments.

options:
  -h, --help            show this help message and exit
  --models {llama13b,llama7b,deepseek} [{llama13b,llama7b,deepseek} ...]
                        Which models to run (default: all).
  --temps {0.01,0.3,0.5,0.7,1.0} [{0.01,0.3,0.5,0.7,1.0} ...]
                        Which temperatures to run (default: all).
  --checkers {semantic,unconstrained,grammar} [{semantic,unconstrained,grammar} ...]
                        Which checker types to run (default: all).
  --output OUTPUT       Path to the output directory (default: experiments/typescript/data).
```

Once the output is generated, tables can be produced using the same procedure as with the raw data, just with the input directory changed to where the results were stored.

# Additional Description
TODO: Add description of directory layout.