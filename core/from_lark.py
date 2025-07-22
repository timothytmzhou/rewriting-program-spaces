import importlib.resources
import lark
import regex
from typing import Callable
from operator import or_
from functools import reduce
from regex import Pattern as Regex
from dataclasses import dataclass
from lark import Lark
from core.rewrite import rewrite
from .parser import Rearrangement, Parser, ConstantParser, Concatenation, Choice
from lexing.leaves import Token
from lexing.lexing import LexerSpec


@dataclass
class Production:
    action: Rearrangement
    symbols: list[str]


@dataclass
class Rule:
    nt: str
    productions: list[Production]


@dataclass
class AttributeGrammar:
    rules: list[Rule]  # One rule for each distinct nonterminal.
    start: str  # Starting nonterminal.
    token_defs: dict[str, Regex]  # Map from token type to Regex.
    ignores: list[str]  # List of token types to ignore.

    def parser_from_sym(self, sym, parsers) -> Parser:
        if sym in self.token_defs:
            return ConstantParser(Token(sym, self.token_defs[sym]))
        return parsers[sym]()

    def parser_from_production(self, production, parsers) -> Parser:
        return Concatenation.of(
            (self.parser_from_sym(sym, parsers) for sym in production.symbols),
            rearrange=production.action,
        )

    def parser_from_rule(self, rule, parsers):
        return rewrite(
            lambda: Choice.of(
                self.parser_from_production(production, parsers)
                for production in rule.productions
            )
        )

    def build_parser(self) -> tuple[LexerSpec, Parser]:
        tokens = frozenset(
            Token(token_type, regex) for token_type, regex in self.token_defs.items()
            if token_type not in self.ignores
        )
        ignore_regex = reduce(or_, (self.token_defs[ignore] for ignore in self.ignores))
        lexer_spec = LexerSpec(tokens, ignore_regex=ignore_regex)

        parsers: dict[str, Callable[[], Parser]] = {}
        for rule in self.rules:
            parsers[rule.nt] = self.parser_from_rule(rule, parsers)  # type: ignore

        return lexer_spec, parsers[self.start]()


def _parse_token_definitions(tree) -> dict[str, Regex]:
    """Extract token definitions from the parse tree."""
    token_defs = {}
    for token_def in tree.find_data("token"):
        token_type, token_regex = token_def.children
        assert isinstance(token_type, lark.Token)
        assert isinstance(token_regex, lark.Token)
        token_defs[token_type.value] = regex.compile(token_regex.value[1:-1])
    return token_defs


def _parse_production(expansion_data, token_defs: dict[str, Regex]) -> Production:
    """Parse a single production from expansion data."""
    rearrange = []
    symbols = []

    for i, element in enumerate(expansion_data[:-1]):
        assert isinstance(element, lark.Tree)
        match element.data:
            case "nonterminal" | "terminal":
                rearrange.append(i)
                assert isinstance(element.children[0], lark.Token)
                symbols.append(element.children[0].value)
            case "literal":
                assert isinstance(element.children[0], lark.Token)
                literal = element.children[0].value
                # Regex of literal removes the quotes.
                token_defs[literal] = regex.compile(regex.escape(literal[1:-1]))
                symbols.append(literal)

    constructor = None
    action_tree = expansion_data[-1]
    if action_tree:
        assert isinstance(action_tree, lark.Tree)
        assert isinstance(action_tree.children[0], lark.Token)
        constructor = action_tree.children[0].value

    action = Rearrangement(constructor, tuple(rearrange))
    return Production(action, symbols)


def _parse_rule(rule, token_defs: dict[str, Regex]) -> Rule:
    """Parse a single rule from the parse tree."""
    lhs, rhs = rule.children
    assert isinstance(lhs, lark.Token)
    assert isinstance(rhs, lark.Tree)
    rule_name = lhs.value

    productions = []
    for expansion in rhs.children:
        assert isinstance(expansion, lark.Tree)
        production = _parse_production(expansion.children, token_defs)
        productions.append(production)

    return Rule(rule_name, productions)


def parse_attribute_grammar(grammar_source: str, start: str) -> AttributeGrammar:
    """Parse an attribute grammar from source string."""
    # Load the attribute grammar file from package resources.
    with importlib.resources.open_text("core.lark", "attribute_grammar.lark") as fp:
        attribute_grammar = fp.read()

    ag_parser = Lark(attribute_grammar, start="start")
    tree = ag_parser.parse(grammar_source)

    token_defs = _parse_token_definitions(tree)
    rules = [_parse_rule(rule, token_defs) for rule in tree.find_data("rule")]

    ignores = []
    for node in tree.find_data("ignore"):
        child = node.children[0]
        assert isinstance(child, lark.Token)
        ignores.append(child.value)

    return AttributeGrammar(rules, start, token_defs, ignores)
