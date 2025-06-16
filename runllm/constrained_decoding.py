from functools import reduce
from core.grammar import is_nonempty
from core.parser import D, Choice, Parser, delta, image
from lexing.lexing import LexerSpec, partial_lex, lex


class RealizabilityChecker:
    def __init__(self, constraint, initial_parser: Parser, lexerspec: LexerSpec):
        self.string = ""
        self.constraint = constraint
        self.parser = initial_parser
        self.lexerspec = lexerspec

    def realizable(self, pref: str, final: bool = False) -> bool:
        """
        Inputs: pref is a prefix.
        final tells you whether to consider the set of strings pref or pref.*
        Returns: True if the set of strings is realizable
        False otherwise.
        """
        # Call lexer
        if not final:
            lexes = partial_lex(pref, self.lexerspec)
        else:
            lexes = lex(pref, self.lexerspec)

        # Build term representing set of possible parse trees
        terms = [reduce(lambda parser, leaf: D(leaf, parser), lex, self.parser)
                 for lex in lexes]
        derived_parser = Choice.of(terms) if not final else delta(Choice.of(terms))

        # Build corresponding set of good ASTs
        good_asts = self.constraint(image(derived_parser))

        # Check nonemptiness of term
        return is_nonempty(good_asts)
