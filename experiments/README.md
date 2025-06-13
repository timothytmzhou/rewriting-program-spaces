To run the current set of experiments, cd to the experiments directory and run 

```python -u run_experiments.py -n -r &> out.txt &```

This will spawn a background process to run the noninterference benchmarks with [ -n ] and without [ -r ] our tool.
A table will be generated in experiments/noninterference/table.txt.
The programs and runtimes for each run will be in experiments/noninterference/results.txt [our tool] and experiments/noninterference/results_raw.txt [ unconstrained ].

The experiments/run_experiments.py script executes sets of experiments based on the cli input.
Each category of experiment maintains an Instrumenter object to track relevant information across executions.
The Instrumenter maintains Totalers which are maps from (prompt #, run #, key) -> value.
If you want to change how/what information is being computed, change Instrumenter.instrument.
To change how information is reported, change Instrumenter.table_row.

The tracking of runtimes is done slightly separately.
There is a global Totaler called GLB_Timer in totaler.py.
Through the timed decorator (also in totaler.py), calls to decorated functions get logged in GLB_Timer.

The results get collected and analyzed in Instrumenter, and Instrumenter.clear clears GLB_Timer between sets of experiments.