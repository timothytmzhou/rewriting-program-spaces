from __future__ import annotations
from dataclasses import dataclass, replace
from .rewrite import fixpoint, rewrite, Term
from .utils import flatten
from .grammar import Union, Application, EmptySet, TreeGrammar
from .lexing.token import Token


class Parser(Term):
    pass


@dataclass(frozen=True)
class ConstantParser(Parser):
    t: Token
    parsed: bool = False

    def __str__(self):
        return f"ConstantParser({self.t}, {self.parsed})"


@dataclass(frozen=True)
class EmptyParser(Parser):
    pass


@dataclass(frozen=True)
class Rearrangement:
    f: type[Application] | None
    reorder: tuple[int, ...]

    def __str__(self):
        return f"{self.f}"


@dataclass(frozen=True)
class Concatenation(Parser):
    parsed: tuple[Parser, ...]
    remaining: tuple[Parser, ...]
    rearrange: Rearrangement

    def subterms(self):
        return self.parsed + self.remaining

    def compact(self, full=False):
        check_empty = parser_empty if full else lambda p: isinstance(p, EmptyParser)
        if any(check_empty(p) for p in self.parsed + self.remaining):
            return EmptyParser()
        return self

    @classmethod
    def of(cls, *children, rearrange: Rearrangement):
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
        return cls((), flattened, rearrange).compact(full=False)

    def __str__(self):
        parsed = ", ".join(str(c) for c in self.parsed)
        remaining = ", ".join(str(c) for c in self.remaining)
        return f"{self.rearrange}({parsed} => {remaining})"


@dataclass(frozen=True)
class Choice(Parser):
    children: frozenset[Parser]

    def subterms(self):
        return self.children

    def compact(self, full=False):
        check_empty = parser_empty if full else lambda p: isinstance(p, EmptyParser)
        new_children = frozenset(c for c in self.children if not check_empty(c))
        if len(new_children) == 1:
            return next(iter(new_children))
        return Choice(new_children) if new_children else EmptyParser()

    @classmethod
    def of(cls, *children):
        flattened = flatten(children, frozenset)
        return cls(flattened).compact(full=False)

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
        case Concatenation(parsed, remaining, _):
            return all(parser_nonempty(c) for c in parsed + remaining)
        case _:
            raise TypeError(f"Unexpected type: {type(p)}")


def parser_empty(p: Parser) -> bool:
    return not parser_nonempty(p)


@rewrite
def D(t: Token, p: Parser) -> Parser:
    match p:
        case ConstantParser(parser_token, False):
            unified = parser_token.update(t)
            return ConstantParser(unified, True) if unified else EmptyParser()
        case Choice(children):
            return Choice.of(D(t, c) for c in children)
        case Concatenation(parsed, remaining, _) if remaining:
            derived = D(t, remaining[0])
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
        case Concatenation(_, remaining, _) if not remaining:
            return p
        case _:
            return EmptyParser()


@rewrite
def image(p: Parser) -> TreeGrammar:
    match p:
        case ConstantParser(t):
            return t
        case EmptyParser():
            return EmptySet()
        case Choice(children):
            return Union.of(image(c) for c in children)
        case Concatenation(parsed, remaining, rearrange):
            concat_children = parsed + remaining
            if rearrange.f is None:
                assert len(rearrange.reorder) == 1
                return image(concat_children[rearrange.reorder[0]])
            return rearrange.f.of(
                (image(concat_children[x]) for x in rearrange.reorder),
                is_tree=not remaining,
            )
        case _:
            raise ValueError(f"Unexpected parser: {p}")
