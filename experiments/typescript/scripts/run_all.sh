#!/bin/bash
if [ $# -ne 1 ]; then
    echo "Usage: $0 <output_directory>"
    exit 1
fi

outdir="$1"
mkdir -p "$outdir"

python run.py -t -o -g --temp 0.01 --output "$outdir" > "$outdir/out_001.txt" 2>&1

python run.py -t -o -g --temp 0.3 --output "$outdir" > "$outdir/out_03.txt" 2>&1

python run.py -t -o -g --temp 0.5 --output "$outdir" > "$outdir/out_05.txt" 2>&1

python run.py -t -o -g --temp 0.7 --output "$outdir" > "$outdir/out_07.txt" 2>&1

python run.py -t -o -g --temp 1.0 --output "$outdir" > "$outdir/out_10.txt" 2>&1
