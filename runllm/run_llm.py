from dataclasses import dataclass
from collections import defaultdict
from typing import Any, List, Tuple, Set, Optional
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForCausalLM,
    PreTrainedTokenizer,
    PreTrainedModel
)
from transformers.cache_utils import DynamicCache

from .constrained_decoding import RealizabilityChecker


@dataclass
class Config:
    """
    Configuration for language model generation.
    """
    # Model configuration
    model_id: str = "codellama/CodeLlama-13b-Instruct-hf"
    device: str = "cuda"
    dtype: torch.dtype = torch.bfloat16

    # Generation parameters
    max_new_tokens: int = 50
    temperature: float = 0.5
    repetition_penalty: float = 1.0
    top_p: float = 1.0
    top_k: float = 0
    num_guesses: int = 50


DEFAULT_CONTEXT = """You are a skilled programmer who responds
to questions by writing concise code without comments.""".replace('\n', '')


class LanguageModelRunner:
    def __init__(self, config: Config):
        self.config = config
        self.device = torch.device(config.device)
        self.model, self.tokenizer = self._load_model_and_tokenizer()

    def _load_model_and_tokenizer(self) -> Tuple[PreTrainedModel, PreTrainedTokenizer]:
        """
        Load and configure the model and tokenizer.
        """
        tokenizer = AutoTokenizer.from_pretrained(self.config.model_id)
        tokenizer.pad_token = tokenizer.eos_token

        model = AutoModelForCausalLM.from_pretrained(self.config.model_id,
                                                     device_map="auto")
        model.to(dtype=self.config.dtype)
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
        generated_tokens: List[int],
        forbidden_tokens: Set[int],
        cache: DynamicCache
    ) -> Any:
        """
        Generate the next token using the model.
        """
        bad_words = [[id] for id in forbidden_tokens] if forbidden_tokens else None
        inp = torch.tensor([list(input_ids[0]) + generated_tokens])
        inp = inp.to(self.config.device)
        return self.model.generate(
            inp,
            do_sample=True,
            pad_token_id=self.tokenizer.eos_token_id,
            eos_token_id=self.tokenizer.eos_token_id,
            max_new_tokens=1,
            temperature=self.config.temperature,
            top_p=self.config.top_p,
            top_k=self.config.top_k,
            bad_words_ids=bad_words,
            repetition_penalty=self.config.repetition_penalty,
            num_return_sequences=1,
            output_scores=True,
            return_dict_in_generate=True,
            past_key_values=cache
        )

    def run(
        self,
        realizability_checker: RealizabilityChecker,
        prompt: str,
        context: str = DEFAULT_CONTEXT
    ) -> Optional[str]:
        """
        Generate a solution that satisfies the realizability checker.
        """
        input_ids = self._tokenize_prompt(prompt, context)
        generated_tokens = []
        forbidden_tokens = defaultdict(set)

        cache = DynamicCache()
        for _ in range(self.config.num_guesses):
            if len(generated_tokens) >= self.config.max_new_tokens:
                break
            output = self._generate_next_token(
                input_ids,
                generated_tokens,
                forbidden_tokens[tuple(generated_tokens)],
                cache
            )
            new_token: int = output.sequences[0][-1].tolist()
            is_final = (new_token == self.tokenizer.eos_token_id)
            decoded_output = self.tokenizer.decode(generated_tokens + [new_token],
                                                   skip_special_tokens=True)
            if realizability_checker.realizable(decoded_output, is_final):
                generated_tokens.append(new_token)
                if is_final:
                    return decoded_output
            else:
                forbidden_tokens[tuple(generated_tokens)].add(new_token)
                cache.crop(-1)

        return None
        
