from __future__ import annotations
from dataclasses import dataclass, field
import functools
import regex
from typing import Iterable
from lexing.leaves import Token


IGNORE = "RESERVED_IGNORE_SORT_TITLE"


@dataclass(frozen=True)
class LexerSpec:
    tokens: frozenset[Token]
    ignore_regex: regex.Pattern = regex.compile(r"^(?!)$")

    def __hash__(self):
        return hash((self.tokens, self.ignore_regex.pattern))

    def get_lexemes(self) -> Iterable[Token]:
        yield from self.tokens
        yield Token(IGNORE, self.ignore_regex)


@dataclass
class LexerState:
    prefix: tuple[Token, ...] = field(default_factory=tuple)
    continuations: set[tuple[Token, ...]] = field(default_factory=lambda: {()})

    def get_partial_lexes(self) -> set[tuple[Token, ...]]:
        return {tuple(self.prefix) + cont for cont in self.continuations}

    def simplify(self) -> LexerState:
        if self.continuations and all(
            cont[len(self.prefix)].nullable() for cont in self.continuations
        ):
            prefix = self.prefix + (next(iter(self.continuations))[0].complete(),)
            continuations = {t[1:] for t in self.continuations}
            return LexerState(prefix, continuations).simplify()
        return self

    def finalize(self) -> LexerState:
        if self.continuations:
            continuations = {
                c[:-1] + (c[-1].complete(),)
                for c in self.continuations
                if c[-1].nullable()
            }
            return LexerState(self.prefix, continuations)
        return self

    def extend_lexer_state(self, char: str, lexerspec: LexerSpec) -> LexerState:
        new_continuations: set[tuple[Token, ...]] = set()
        for state in self.continuations:
            if len(state) == 0:
                for lexeme in lexerspec.get_lexemes():
                    derived = lexeme.extend(char)
                    if derived.nonempty():
                        new_continuations.add((derived,))
            else:
                if state[-1].nullable():
                    for lexeme in lexerspec.get_lexemes():
                        derived = lexeme.extend(char)
                        if derived.nonempty():
                            new_continuations.add(
                                (state[:-1] + (state[-1].complete(), derived))
                            )
                if state[-1].extend(char).nonempty():
                    new_continuations.add(state[:-1] + (state[-1].extend(char),))
        return LexerState(self.prefix, new_continuations)

    def remove_nonmaximal_munch(self):
        result = set(self.continuations)
        for state in self.continuations:
            for state2 in result:
                for i in range(min(len(state), len(state2))):
                    if state[i] != state2[i]:
                        if (
                            len(state[i].prefix) < len(state2[i].prefix)
                            and state2[i].nullable()
                        ):
                            result.remove(state)
                        break
                if state not in result:
                    break
        self.continuations = result

    def remove_ignorable_tokens(self) -> LexerState:
        continuations = {
            tuple(filter(lambda x: x.token_type != IGNORE, state))
            for state in self.continuations
        }
        return LexerState(self.prefix, continuations)


def partial_lex(inp: str, lexerspec: LexerSpec):
    return lex(inp, lexerspec, final=False)


def lex(inp: str, lexerspec: LexerSpec, final=True):
    lstate = compute_lexer_state(inp, lexerspec)
    if final:
        lstate = lstate.finalize()
    lstate = lstate.remove_ignorable_tokens()
    return lstate.get_partial_lexes()


@functools.lru_cache
def compute_lexer_state(inp: str, lexerspec: LexerSpec) -> LexerState:
    if len(inp) == 0:
        return LexerState()
    lstate = compute_lexer_state(inp[:-1], lexerspec)
    lstate = lstate.extend_lexer_state(inp[-1], lexerspec)
    lstate.remove_nonmaximal_munch()
    return lstate
