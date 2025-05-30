from collections import defaultdict
import torch
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM, PreTrainedTokenizer, PreTrainedModel
from .constrained_decoding import RealizabilityChecker
from typing import Any


def load_model_and_tokenizer(model_id: str, dtype: torch.dtype):
    # Load tokenizer
    tokenizer: PreTrainedTokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.pad_token = tokenizer.eos_token

    # Load model
    model: PreTrainedModel = AutoModelForCausalLM.from_pretrained(model_id, device_map="auto")
    model.to(dtype=dtype)  # type: ignore
    model.resize_token_embeddings(len(tokenizer))  # type: ignore
    return model, tokenizer


def tokenize_prompt(tokenizer: PreTrainedTokenizer, prompt: str, model):
    # Tokenize prompt into ids
    input_ids: torch.Tensor = tokenizer(
        prompt, add_special_tokens=False, return_tensors="pt", padding=True
    )["input_ids"]
    input_ids = input_ids.to(model.device)
    return input_ids


def generate_solution(
        model, tokenizer: PreTrainedTokenizer, input_ids,
        realizability_checker: RealizabilityChecker,
        max_new_tokens, temp, repetition_penalty, top_p, top_k,
        forbidden_tokens: defaultdict[Any, set[int]],
        num_guesses: int = 100) -> str:
    # Initialize checker
    generated_tokens: list[int] = []

    # Check if problem is unrealizable
    if not realizability_checker.realizable(""):
        return "NO SOLUTION"

    # Generate a solution
    while (
        len(generated_tokens) < max_new_tokens
        and (not generated_tokens or (generated_tokens[-1] != tokenizer.eos_token_id))
    ):
        # If no possible tokens remain or num_guesses exceeded, end string or backtrack
        if len(forbidden_tokens[tuple(generated_tokens)]) == min(num_guesses, len(tokenizer)):
            # Try to end the string if the string is valid; else backtrack
            if realizability_checker.realizable(
                    tokenizer.decode(generated_tokens, skip_special_tokens=True),
                    True):
                return tokenizer.decode(generated_tokens, skip_special_tokens=True)
            else:
                forbidden_tokens[tuple(generated_tokens[:-1])].add(generated_tokens[-1])
                generated_tokens = generated_tokens[:-1]
                continue

        # Otherwise, generate the next token
        bad_words = list(map(lambda id: [id], forbidden_tokens[tuple(generated_tokens)]))
        output = model.generate(
            torch.tensor([list(input_ids[0]) + generated_tokens]),
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
            max_new_tokens=1,
            top_p=top_p,
            top_k=top_k,
            temperature=temp,
            bad_words_ids=bad_words if bad_words else None,
            repetition_penalty=repetition_penalty,
            num_return_sequences=1,
            return_dict_in_generate=True,
            output_scores=True,
        )
        output = output.sequences[0][len(input_ids[0]):].tolist()
        final = (output[-1] == tokenizer.eos_token_id)
        print(tokenizer.decode(output, skip_special_tokens=True))

        # Check realizability and accept valid tokens or forbid suggestion
        if realizability_checker.realizable(
                tokenizer.decode(output, skip_special_tokens=True),
                final):
            generated_tokens = output
        else:
            forbidden_tokens[tuple(generated_tokens)].add(output[-1])
    # Detokenize generated output
    return tokenizer.decode(generated_tokens, skip_special_tokens=True)


def run_llm(
        realizability_checker: RealizabilityChecker,
        prompt: str,
        num_iter: int = 1,
        model_id: str = "TinyLlama/TinyLlama_v1.1",
        device="cpu",
        dtype: torch.dtype = torch.bfloat16,
        max_new_tokens: int = 100,
        temp: float = 1.0,
        repetition_penalty: float = 1.0,
        top_p: float = 1.0,
        top_k: float = 0):

    device = torch.device(device)
    model, tokenizer = load_model_and_tokenizer(model_id, dtype)
    input_ids = tokenize_prompt(tokenizer, prompt, model)
    outputs: list[str] = []
    # Initialize map to track forbidden tokens
    forbidden_tokens: defaultdict[Any, set[int]] = defaultdict(set)
    for _ in tqdm(range(num_iter), desc="Running Inference"):
        result = generate_solution(
            model, tokenizer, input_ids, realizability_checker,
            max_new_tokens, temp, repetition_penalty, top_p, top_k,
            forbidden_tokens, 10
        )
        outputs.append(result)
    return outputs
