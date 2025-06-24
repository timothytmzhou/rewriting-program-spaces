import regex
from enum import Enum
from core.rewrite import rewrite
from core.parser import *
from lexing.leaves import Token
from lexing.lexing import LexerSpec


TokenTypes = Enum("TokenTypes", "ID INT LPAR RPAR LET EQUALS IN PLUS TIMES")


def make_token(name, pattern: str) -> Token:
    return Token(TokenTypes[name], regex.compile(pattern))


ID = make_token("ID", r"[a-zA-Z_][a-zA-Z0-9_]*")
INT = make_token("INT", r"\d+")
LPAR = make_token("LPAR", r"\(")
RPAR = make_token("RPAR", r"\)")
LET = make_token("LET", r"let")
EQUALS = make_token("EQUALS", r"=")
IN = make_token("IN", r"in")
PLUS = make_token("PLUS", r"\+")
TIMES = make_token("TIMES", r"\*")

lexer_spec = LexerSpec(
    tokens=frozenset({ID, INT, LPAR, RPAR, LET, EQUALS, IN, PLUS, TIMES}),
    ignore_regex=regex.compile(r"\s+")
)


@rewrite
def Id() -> Parser:
    return Concatenation.of(
        ConstantParser(ID),
        rearrange=Rearrangement("Var", (0,))
    )


@rewrite
def Num() -> Parser:
    return Concatenation.of(
        ConstantParser(INT),
        rearrange=Rearrangement("Num", (0,))
    )


@rewrite
def Atom() -> Parser:
    return Choice.of(
        Id(),
        Num(),
        Concatenation.of(
            ConstantParser(LPAR), E(), ConstantParser(RPAR),
            rearrange=Rearrangement(None, (1,))
        )
    )


@rewrite
def App() -> Parser:
    return Choice.of(
        Atom(),
        Concatenation.of(App(), Atom(),
                         rearrange=Rearrangement("App", (0, 1)))
    )


@rewrite
def Mul() -> Parser:
    return Choice.of(
        App(),
        Concatenation.of(Mul(), ConstantParser(TIMES), App(),
                         rearrange=Rearrangement("Mult", (0, 2)))
    )


@rewrite
def Add() -> Parser:
    return Choice.of(
        Mul(),
        Concatenation.of(Add(), ConstantParser(PLUS), Mul(),
                         rearrange=Rearrangement("Add", (0, 2)))
    )


@rewrite
def E() -> Parser:
    return Choice.of(
        Add(),
        Concatenation.of(
            ConstantParser(LET), Id(), ConstantParser(EQUALS), E(),
            ConstantParser(IN), E(),
            rearrange=Rearrangement("Let", (1, 3, 5))
        )
    )
