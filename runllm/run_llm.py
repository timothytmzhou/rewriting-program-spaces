import gc
from dataclasses import dataclass
from collections import Counter, defaultdict
from typing import Any, List, Tuple, Set, Optional
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    PreTrainedTokenizer,
    PreTrainedModel
)
from transformers.cache_utils import DynamicCache
import time


@dataclass
class ModelConfig:
    model_id: str = "codellama/CodeLlama-13b-Instruct-hf"
    device: str = "cuda"
    dtype: torch.dtype = torch.bfloat16


@dataclass
class Config:
    """
    Configuration for language model generation.
    """
    # Generation parameters
    max_new_tokens: int = 300
    temperature: float = 0.5
    repetition_penalty: float = 1.0
    top_p: float = 1.0
    top_k: float = 0
    num_guesses: int = 300


DEFAULT_CONTEXT = """You are a skilled programmer who responds
to questions by writing concise code without comments.""".replace('\n', '')

@dataclass
class RunInfo:
    llm_finished: bool
    output: str
    total_realizability_time: float
    num_tokens_guessed: int
    num_tokens_generated: int
    tries_per_token: Counter


class LanguageModelRunner:
    def __init__(self, model_config: ModelConfig = ModelConfig()):
        self.model_config = model_config
        self.device = torch.device(model_config.device)
        self.model, self.tokenizer = self._load_model_and_tokenizer()

    def _load_model_and_tokenizer(self) -> Tuple[PreTrainedModel, PreTrainedTokenizer]:
        """
        Load and configure the model and tokenizer.
        """
        tokenizer = AutoTokenizer.from_pretrained(self.model_config.model_id)
        tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(self.model_config.model_id,
                                                     device_map="auto")
        model.to(dtype=self.model_config.dtype)
        model.resize_token_embeddings(len(tokenizer))
        return model, tokenizer

    def _tokenize_prompt(self, prompt: str, context: str) -> torch.Tensor:
        """
        Process and tokenize the input prompt.
        """
        messages = [
            {"role": "system", "content": context},
            {"role": "user", "content": prompt},
        ]
        input_ids: torch.Tensor = self.tokenizer.apply_chat_template(
            messages, tokenize=True,
            add_generation_prompt=True, add_special_tokens=False,
            return_tensors="pt", padding=True
        )
        return input_ids.to(self.model.device)

    def _generate_next_token(
        self,
        input_ids: torch.Tensor,
        config: Config,
        generated_tokens: List[int],
        forbidden_tokens: Set[int],
        cache: DynamicCache
    ) -> Any:
        """
        Generate the next token using the model.
        """
        bad_words = [[id]
                     for id in forbidden_tokens] if forbidden_tokens else None
        inp = torch.tensor([list(input_ids[0]) + generated_tokens])
        inp = inp.to(self.model_config.device)
        if self.tokenizer.eos_token_id in forbidden_tokens:
            eos_token_id = None
        else:
            eos_token_id = self.tokenizer.eos_token_id
        return self.model.generate(
            inp,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id,
            eos_token_id=eos_token_id,
            max_new_tokens=1,
            temperature=config.temperature,
            top_p=config.top_p,
            top_k=config.top_k,
            bad_words_ids=bad_words,
            repetition_penalty=config.repetition_penalty,
            num_return_sequences=1,
            output_scores=True,
            return_dict_in_generate=True,
            past_key_values=cache,
        )

    def run(
        self,
        config: Config,
        prompt: str,
        context: str = DEFAULT_CONTEXT,
        realizability_checker=None
    ) -> RunInfo:
        input_ids = self._tokenize_prompt(prompt, context)
        generated_tokens = []
        forbidden_tokens = defaultdict(set)
        num_tokens_guessed = 0
        cache = DynamicCache()
        decoded_output = ""
        total_realizability_time = 0.0
        tries = 0
        try_counts = Counter()

        for _ in range(config.num_guesses):
            if len(generated_tokens) >= config.max_new_tokens:
                break
            num_tokens_guessed += 1
            tries += 1
            output = self._generate_next_token(
                input_ids,
                config,
                generated_tokens,
                forbidden_tokens[tuple(generated_tokens)],
                cache
            )
            new_token: int = output.sequences[0][-1].tolist()
            is_final = (new_token == self.tokenizer.eos_token_id)
            decoded_output = self.tokenizer.decode(generated_tokens + [new_token],
                                                   skip_special_tokens=True)
            if realizability_checker is None:
                is_realizable = True
            else:
                check_start = time.time()
                is_realizable = realizability_checker.realizable(decoded_output, is_final)
                total_realizability_time += time.time() - check_start
            if is_realizable:
                try_counts[tries] += 1
                tries = 0 
                generated_tokens.append(new_token)
                if is_final:
                    return RunInfo(
                        llm_finished=True,
                        output=decoded_output,
                        total_realizability_time=total_realizability_time,
                        num_tokens_guessed=num_tokens_guessed,
                        num_tokens_generated=len(generated_tokens),
                        tries_per_token=try_counts
                    )
            else:
                forbidden_tokens[tuple(generated_tokens)].add(new_token)
                cache.crop(-1)

        return RunInfo(
            llm_finished=False,
            output=decoded_output,
            total_realizability_time=total_realizability_time,
            num_tokens_guessed=num_tokens_guessed,
            num_tokens_generated=len(generated_tokens),
            tries_per_token=try_counts
        )

    def __del__(self):
        del self.model
        del self.tokenizer
        gc.collect()
        torch.cuda.empty_cache()
