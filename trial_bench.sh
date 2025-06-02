#!/bin/bash

total=0
for i in {1..10}
do
	t=$( (time -p pytest tests/test_noninterference.py) 2>&1 | awk '/real/ {print $2}')
	total=$(echo "$total + $t" | bc)
done
avg=$(echo "scale=2; $total / 10" | bc)
echo "Average time: $avg seconds"
