from __future__ import annotations
from dataclasses import dataclass, field, replace
import greenery as grn

from lexing.leaves import EPS, RegexLeaf


IGNORE = "RESERVED_IGNORE_SORT_TITLE"


@dataclass
class LexerSpec:
    tok2regex: frozenset[RegexLeaf]
    ignore_regex: grn.Pattern = grn.NULL

    def __post_init__(self):
        # TODO: Fix hash function or remove
        # self.hash = hash(frozenset(self.tok2regex).union([self.ignore_regex]))
        self.hash = 1

    def __hash__(self):
        return self.hash

    def get_lexemes(self) -> list[RegexLeaf]:
        return ([RegexLeaf(IGNORE, self.ignore_regex, "")] + list(self.tok2regex))


@dataclass
class LexerState:
    prefix: tuple[RegexLeaf, ...] = field(default_factory=tuple)
    continuations: set[tuple[RegexLeaf, ...]] = field(default_factory=lambda: {()})

    def get_partial_lexes(self) -> set[tuple[RegexLeaf, ...]]:
        return {tuple(self.prefix) + cont for cont in self.continuations}

    def simplify(self) -> LexerState:
        if (
            self.continuations
            and all(cont[len(self.prefix)].nullable()for cont in self.continuations)
        ):
            prefix = self.prefix + next(iter(self.continuations))
            continuations = {t[1:] for t in self.continuations}
            return LexerState(prefix, continuations).simplify()
        return self

    def finalize(self) -> LexerState:
        if self.continuations:
            continuations = {c[:-1] + (replace(c[-1], remainder=EPS),)
                             for c in self.continuations if c[-1].nullable()}
            return LexerState(self.prefix, continuations)
        return self

    def extend_lexer_state(self, char: str, lexerspec: LexerSpec) -> LexerState:
        new_continuations: set[tuple[RegexLeaf, ...]] = set()
        for state in self.continuations:
            if len(state) == 0:
                for lexeme in lexerspec.get_lexemes():
                    derived = lexeme.deriv(char)
                    if derived.nonempty():
                        new_continuations.add((derived,))
            else:
                if state[-1].nullable():
                    for lexeme in lexerspec.get_lexemes():
                        derived = lexeme.deriv(char)
                        if derived.nonempty():
                            new_continuations.add((
                                state[:-1] + (replace(state[-1], remainder=EPS),) + (derived,)))
                if state[-1].deriv(char).nonempty():
                    new_continuations.add(state[:-1] + (state[-1].deriv(char),))
        return LexerState(self.prefix, new_continuations)

    def remove_nonmaximal_munch(self):
        result = set(self.continuations)
        for state in self.continuations:
            for state2 in result:
                for i in range(min(len(state), len(state2))):
                    if state[i] != state2[i]:
                        if len(state[i].prefix) < len(state2[i].prefix) and state2[i].nullable():
                            result.remove(state)
                        break
                if state not in result:
                    break
        self.continuations = result

    def remove_ignorable_tokens(self) -> LexerState:
        continuations = {
            tuple(filter(lambda x: x.sort != IGNORE, state)) for state in self.continuations}
        return LexerState(self.prefix, continuations)


def partial_lex(inp: str, lexerspec: LexerSpec):
    lstate = compute_lexer_state(inp, lexerspec)
    lstate = lstate.remove_ignorable_tokens()
    return lstate.get_partial_lexes()


def lex(inp: str, lexerspec: LexerSpec):
    lstate = compute_lexer_state(inp, lexerspec)
    lstate = lstate.finalize()
    lstate = lstate.remove_ignorable_tokens()
    return lstate.get_partial_lexes()


# @functools.lru_cache
def compute_lexer_state(inp: str, lexerspec: LexerSpec) -> LexerState:
    if len(inp) == 0:
        return LexerState()
    lstate = compute_lexer_state(inp[:-1], lexerspec)
    lstate = lstate.extend_lexer_state(inp[-1], lexerspec)
    lstate.remove_nonmaximal_munch()
    return lstate
