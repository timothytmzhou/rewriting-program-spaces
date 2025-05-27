from runllm.constrained_decoding import RealizabilityChecker
from runllm.run_llm import run_llm
a = RealizabilityChecker(None, None, None, None)
print(run_llm(a, "hi!"))
