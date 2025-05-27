from collections import defaultdict
import torch
from tqdm import tqdm
from transformers import AutoTokenizer, AutoModelForCausalLM, PreTrainedTokenizer, PreTrainedModel
from .constrained_decoding import RealizabilityChecker
from typing import Any


def load_model_and_tokenizer(model_id: str, dtype: torch.dtype):
    # Load tokenizer
    tokenizer: PreTrainedTokenizer = AutoTokenizer.from_pretrained(model_id)
    tokenizer.pad_token = "[PAD]"
    # tokenizer.pad_token = tokenizer.eos_token

    # Load model
    model: PreTrainedModel = AutoModelForCausalLM.from_pretrained(model_id, device_map="auto")
    model.to(dtype=dtype)  # type: ignore
    model.resize_token_embeddings(len(tokenizer))  # type: ignore
    return model, tokenizer


def tokenize_prompt(tokenizer: PreTrainedTokenizer, prompt: str, model: PreTrainedModel):
    # Tokenize prompt into ids
    input_ids: torch.Tensor = tokenizer(
        prompt, add_special_tokens=False, return_tensors="pt", padding=True
    )["input_ids"]
    input_ids = input_ids.to(model.device)
    print(input_ids)


def generate_solution(
        model, tokenizer, input_ids, realizability_checker,
        max_new_tokens, temp, repetition_penalty, top_p, top_k,
        forbidden_tokens):
    # Initialize checker
    generated_tokens: list = []

    # Check if problem is unrealizable
    if not realizability_checker.realizable(""):
        return "NO SOLUTION"

    # Generate a solution
    while (len(generated_tokens) < max_new_tokens
            and (not generated_tokens or (generated_tokens[-1] != tokenizer.eos_token_id))):

        # If no possible tokens remain, backtrack
        if len(forbidden_tokens[tuple(generated_tokens)]) == len(tokenizer):
            forbidden_tokens[tuple(generated_tokens[:-1])].add(generated_tokens[-1])
            generated_tokens = generated_tokens[:-1]
            continue

        # Otherwise, generate the next token
        output = model.generate(
            input_ids + generated_tokens,
            do_sample=True,
            pad_token_id=tokenizer.eos_token_id,
            eos_token_id=tokenizer.eos_token_id,
            max_new_tokens=1,
            top_p=top_p,
            top_k=top_k,
            temperature=temp,
            bad_words_ids=list(forbidden_tokens[tuple(generated_tokens)]),
            repetition_penalty=repetition_penalty,
            num_return_sequences=1,
            return_dict_in_generate=True,
            output_scores=True,
        )
        output = output[len(input_ids):]

        # Else, check realizability and accept valid tokens or forbid suggestion
        if realizability_checker.realizable(
                tokenizer.decode(output, skip_special_tokens=True)):
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
    print(input_ids)
    outputs = []
    # Initialize map to track forbidden tokens
    forbidden_tokens: defaultdict[Any, set[int]] = defaultdict(set)
    for _ in tqdm(range(num_iter), desc="Running Inference"):
        result = generate_solution(
            model, tokenizer, input_ids, realizability_checker,
            max_new_tokens, temp, repetition_penalty, top_p, top_k,
            forbidden_tokens
        )
        outputs.append(result)
    return outputs
