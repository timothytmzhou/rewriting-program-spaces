from functools import reduce
from core.parser import D, Choice, delta, parser_nonempty
from lexing.lexing import LexerSpec, partial_lex, lex


class RealizabilityChecker:
    def __init__(self, constraint, initial_grammar, image, lexerspec: LexerSpec):
        self.string = ""
        self.constraint = constraint
        self.grammar = initial_grammar
        self.image = image
        self.lexerspec = lexerspec

    def realizable(self, pref: str, final: bool = False) -> bool:
        """
        Inputs: pref is a prefix.
        final tells you whether to consider the set of strings pref or pref.*
        Returns: True if the set of strings is realizable
        False otherwise.
        """
        # Call lexer
        lexes = partial_lex(pref, self.lexerspec) if not final else lex(pref, self.lexerspec)

        # Build term representing set of possible parse trees
        terms = [reduce(lambda parser, leaf: D(leaf, parser), lex, self.grammar) for lex in lexes]
        big_term = Choice.of(terms) if not final else delta(Choice.of(terms))

        # TODO: Build corresponding set of good ASTs

        # TODO: Check nonemptiness of term
        return parser_nonempty(big_term)
