
from core.parser import EmptyParser
from lexing.lexing import LexerSpec
from runllm.constrained_decoding import RealizabilityChecker


checker = RealizabilityChecker(lambda x: x,
                               EmptyParser(),
                               LexerSpec(frozenset()))
