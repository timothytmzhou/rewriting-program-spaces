Proposed Evaluation Plan:

Our 3 runtime variables are grammar size, complexity of analysis, and program length. The following experiments show we are sufficiently robust in each.

Experiment 1 [Variable-size programs on a large grammar]: Choose 5 large files in Python's standard library. Use a realizability checker that only checks Python grammaticality. For each prefix of each file, plot realizability time/token vs program length (# characters) [Slightly similar to Figure 6 [here](https://dl.acm.org/doi/pdf/10.1145/2908080.2908128)]. Using a large grammar like Python solves concerns about scaling with grammar size. The plot also shows robustness in program length.

Experiment 2: [Variable-size analyses] Generate a large noninterference program with 200 vars x_1, ..., x_200. For each i, instantiate a realizability typechecker that guarantees that information from x_j does not flow to x_{j+1} for j less than i. Plot realizability time for large program vs i. This plot demonstrates robustness in analysis size.