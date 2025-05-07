from __future__ import annotations
from dataclasses import dataclass
from .rewrite import *
from .utils import flatten
from .grammar import *


class Parser(Term):
    pass


@dataclass(frozen=True)
class ConstantParser[T](Parser):
    c: T
    parsed: bool = False


@dataclass(frozen=True)
class EmptyParser(Parser):
    pass


@dataclass
class Concatenation(Parser):
    f: Symbol
    parsed: tuple[Parser]  # TODO: make this TreeGrammar instead?
    remaining: tuple[Parser]
    rearrange: tuple[int]

    def __init__(self, f, *children, rearrange=None):
        """
        Builds a parser that emits ASTS of form f(x_1, x_2, ..., x_n) where
        x_i are the parsed subtrees.
        :param f: The function to apply to the parsed subtrees.
        :param children: The remaining parsers to apply.
        :param rearrange: The order in which to rearrange the parsed subtrees when emitting ASTs.
        """
        self.f = f
        self.parsed = ()
        self.remaining = flatten(children, tuple)
        if rearrange is None:
            self.rearrange = tuple(range(len(self.remaining)))
        else:
            self.rearrange = tuple(rearrange)

    def __hash__(self):
        return hash((self.f, self.parsed, self.remaining, self.rearrange))


@dataclass
class Choice(Parser):
    children: frozenset[Parser]

    def __init__(self, *children):
        self.children = flatten(children, frozenset)

    def __hash__(self):
        return hash(self.children)


@rewrite
def D(x, p: Parser):
    match p:
        case ConstantParser(c, False) if c == x:
            return ConstantParser(c, True)
        case Choice(children):
            return Choice(D(x, c) for c in children)
        case Concatenation(f, parsed, remaining) if remaining:
            derived = D(x, remaining[0])
            return Choice(
                Concatenation(f, parsed, (derived, *remaining[1:])),
                Concatenation(f, parsed + (delta(derived),), remaining[1:])
            )
        case _:
            return EmptyParser()


@rewrite
def delta(p: Parser) -> Parser:
    match p:
        case ConstantParser(c, True):
            return ConstantParser(c)
        case Choice(children):
            return Choice(delta(c) for c in children)
        case Concatenation(f, parsed, remaining) if not remaining:
            return Concatenation(f, parsed)
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
            return Union(image(c) for c in children)
        case Concatenation(f, parsed, remaining, rearrange):
            concat_children: tuple[Parser, ...] = parsed + remaining
            return Application(
                f,
                (image(concat_children[i]) for i in rearrange)
            )
        case _:
            raise TypeError(f"Unexpected type: {type(p)}")
