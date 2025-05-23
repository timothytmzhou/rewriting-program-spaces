class RealizabilityChecker:
    def __init__(self, constraint, initial_grammar, image, lexer):
        self.string = ""
        self.constraint = constraint
        self.initial_grammar = initial_grammar
        self.image = image
        self.lexer = lexer

    def realizable(self, str) -> bool:
        """
        True if the str logged string is realizable
        False otherwise.
        """
        # TODO: Call lexer

        # TODO: Build term, applying constraint function symbol to outside

        # TODO: Check nonemptiness of term
        return True
