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
    max_new_tokens: int = 100
    temperature: float = 0.5
    repetition_penalty: float = 1.0
    top_p: float = 1.0
    top_k: float = 0
    num_guesses: int = 10



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

        model = AutoModelForCausalLM.from_pretrained(self.config.model_id)
        model.to(dtype=self.config.dtype)
        model.resize_token_embeddings(len(tokenizer))
        return model, tokenizer

    def _tokenize_prompt(self, prompt: str) -> torch.Tensor:
        """
        Tokenize the input prompt.
        """
        input_ids = self.tokenizer(
            prompt,
            add_special_tokens=False,
            return_tensors="pt",
            padding=True
        )["input_ids"]
        return input_ids.to(self.model.device)

    def _generate_next_token(
        self,
        input_ids: torch.Tensor,
        generated_tokens: List[int],
        forbidden_tokens: Set[int]
    ):
        """
        Generate the next token using the model.
        """
        bad_words = [[id] for id in forbidden_tokens] if forbidden_tokens else None
        return self.model.generate(
            torch.tensor([list(input_ids[0]) + generated_tokens]),
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
            return_dict_in_generate=True,
            output_scores=True,
        )

    def run(
        self,
        realizability_checker: RealizabilityChecker,
        prompt: str
    ) -> Optional[str]:
        """
        Generate a solution that satisfies the realizability checker.
        """
        input_ids = self._tokenize_prompt(prompt)
        generated_tokens: List[int] = []
        forbidden_tokens: defaultdict[Any, Set[int]] = defaultdict(set)

        if not realizability_checker.realizable(""):
            return None

        while len(generated_tokens) < self.config.max_new_tokens:
            output = self._generate_next_token(
                input_ids,
                generated_tokens,
                forbidden_tokens[tuple(generated_tokens)]
            )
            
            new_tokens = output.sequences[0][len(input_ids[0]):].tolist()
            is_final = (new_tokens[-1] == self.tokenizer.eos_token_id)
            decoded_output = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
            
            if realizability_checker.realizable(decoded_output, is_final):
                generated_tokens = new_tokens
            else:
                forbidden_tokens[tuple(generated_tokens)].add(new_tokens[-1])

            if generated_tokens and generated_tokens[-1] == self.tokenizer.eos_token_id:
                break

        return self.tokenizer.decode(generated_tokens, skip_special_tokens=True)


def run_llm(
    realizability_checker: RealizabilityChecker,
    prompt: str,
    **kwargs
) -> List[str]:
    """
    Legacy interface for backward compatibility.
    """
    config = Config(**kwargs)
    runner = LanguageModelRunner(config)
    return runner.run(realizability_checker, prompt)
