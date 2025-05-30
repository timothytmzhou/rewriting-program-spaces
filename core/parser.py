from __future__ import annotations
from dataclasses import dataclass, replace
from .rewrite import *
from .utils import flatten
from .grammar import *


class Parser(Term):
    pass


@dataclass(frozen=True)
class ConstantParser(Parser):
    c: Leaf
    parsed: bool = False

    def __str__(self):
        return f"ConstantParser({self.c}, {self.parsed})"


@dataclass(frozen=True)
class EmptyParser(Parser):
    pass


@dataclass(frozen=True)
class Concatenation(Parser):
    f: Symbol
    parsed: tuple[Parser, ...]
    remaining: tuple[Parser, ...]
    rearrange: tuple[int, ...]

    def subterms(self):
        return self.parsed + self.remaining

    def compact(self):
        if any(parser_empty(p) for p in self.parsed + self.remaining):
            return EmptyParser()
        return self

    @classmethod
    def of(cls, f, *children, rearrange=None):
        """
        Builds a parser that emits ASTS of form f(x_1, x_2, ..., x_n) where
        x_i are the parsed subtrees.
        :param f: The function to apply to the parsed subtrees.
        :param children: The remaining parsers to apply. Either multiple parsers
                         or a single iterable of parsers.
        :param rearrange: The order (tuple of ints) in which to rearrange
                          the parsed subtrees when emitting ASTs.
        """
        flattened = flatten(children, tuple)
        if any(isinstance(c, EmptyParser) for c in flattened):
            return EmptyParser()
        rearrange = tuple(range(len(flattened))) if rearrange is None else rearrange
        return cls(f, (), flattened, rearrange)

    def __str__(self):
        parsed = ', '.join(str(c) for c in self.parsed)
        remaining = ', '.join(str(c) for c in self.remaining)
        return f"{self.f}({parsed} => {remaining})"


@dataclass(frozen=True)
class Choice(Parser):
    children: frozenset[Parser]

    def subterms(self):
        return self.children

    def compact(self):
        return Choice.of(p for p in self.children if parser_nonempty(p))

    @classmethod
    def of(cls, *children):
        flattened = flatten(children, frozenset) - {EmptyParser()}
        if not flattened:
            return EmptyParser()
        return cls(flattened)

    def __str__(self):
        return " | ".join(str(c) for c in self.children)


@fixpoint(lambda: False)
def parser_nonempty(p: Parser) -> bool:
    match p:
        case EmptyParser():
            return False
        case ConstantParser():
            return True
        case Choice(children):
            return any(parser_nonempty(c) for c in children)
        case Concatenation(_, parsed, remaining):
            return all(parser_nonempty(c) for c in parsed + remaining)
        case _:
            raise TypeError(f"Unexpected type: {type(p)}")


def parser_empty(p: Parser) -> bool:
    return not parser_nonempty(p)


@rewrite
def D(x, p: Parser) -> Parser:
    match p:
        case ConstantParser(c, False):
            inter = c.update(x)
            if inter:
                return ConstantParser(inter, True)
            return EmptyParser()
        case Choice(children):
            return Choice.of(D(x, c) for c in children)
        case Concatenation(_, parsed, remaining) if remaining:
            derived = D(x, remaining[0])
            return Choice.of(
                replace(p, remaining=(derived,) + remaining[1:]),
                replace(p, parsed=parsed + (delta(derived),), remaining=remaining[1:]),
            )
        case _:
            return EmptyParser()


@rewrite
def delta(p: Parser) -> Parser:
    match p:
        case ConstantParser(_, True):
            return p
        case Choice(children):
            return Choice.of(delta(c) for c in children)
        case Concatenation() if not p.remaining:
            return p
        case _:
            return EmptyParser()


@rewrite
def image(p: Parser) -> TreeGrammar:
    match p:
        case ConstantParser(c):
            return Constant(c)
        case EmptyParser():
            return EmptySet()
        case Choice(children):
            return Union.of(image(c) for c in children)
        case Concatenation(f, parsed, remaining, rearrange):
            concat_children = [image(c) for c in parsed + remaining]
            return Application.of(
                f,
                (concat_children[i] for i in rearrange)
            )
        case _:
            raise TypeError(f"Unexpected type: {type(p)}")
