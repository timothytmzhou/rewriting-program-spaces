from __future__ import annotations
from dataclasses import dataclass, replace
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


@dataclass(frozen=True)
class Concatenation(Parser):
    f: Symbol
    parsed: tuple[TreeGrammar]
    remaining: tuple[Parser]
    rearrange: tuple[int]

    @classmethod
    def of(cls, f, *children, rearrange=None):
        """
        Builds a parser that emits ASTS of form f(x_1, x_2, ..., x_n) where
        x_i are the parsed subtrees.
        :param f: The function to apply to the parsed subtrees.
        :param children: The remaining parsers to apply. Either multiple parserrs or a single iterable of parsers.
        :param rearrange: The order in which to rearrange the parsed subtrees when emitting ASTs.
        """
        if rearrange is None:
            rearrange = tuple(range(len(children)))
        else:
            rearrange = tuple(rearrange)
        return cls(f, (), flatten(children, tuple), rearrange)


@dataclass(frozen=True)
class Choice(Parser):
    children: frozenset[Parser]

    @classmethod
    def of(cls, *children):
        return cls(flatten(children, frozenset))


@rewrite
def D(x, p: Parser):
    match p:
        case ConstantParser(c, False) if c == x:
            return ConstantParser(c, True)
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
def delta(p: Parser) -> TreeGrammar:
    match p:
        case ConstantParser(c, True):
            return Constant(c)
        case Choice(children):
            return Union.of(delta(c) for c in children)
        case Concatenation(f, parsed, remaining) if not remaining:
            return Application.of(f, parsed)
        case _:
            return EmptySet()


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
            concat_children = list(parsed) + [image(r) for r in remaining]
            return Application.of(
                f,
                (concat_children[i] for i in rearrange)
            )
        case _:
            raise TypeError(f"Unexpected type: {type(p)}")
