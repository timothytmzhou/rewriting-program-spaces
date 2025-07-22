import regex as re
from enum import Enum

from core.parser import *
from core.grammar import *
from lexing.leaves import Token
from lexing.lexing import LexerSpec
from llm.realizability import RealizabilityChecker


# SYNTAX
LOWVARLEAF = Token("l", re.compile("l"))
HIGHVARLEAF = Token("h", re.compile("h"))
INTSLEAF = Token("int", re.compile("0|([1-9][0-9]*)"))
PLUSLEAF = Token("+", re.compile("\\+"))
MINUSLEAF = Token("-", re.compile("\\-"))
TIMESLEAF = Token("*", re.compile("\\*"))
DIVLEAF = Token("/", re.compile("/"))
LESSLEAF = Token("<", re.compile("<"))
LESSEQLEAF = Token("<=", re.compile("<="))
GREATERLEAF = Token(">", re.compile(">"))
GREATEREQLEAF = Token(">=", re.compile(">="))
EQUALLEAF = Token("=", re.compile("=="))
GETSLEAF = Token(":=", re.compile(":="))
SKIPLEAF = Token("skip", re.compile("skip;"))
SEMICOLONLEAF = Token(";", re.compile(";"))
IFLEAF = Token("if", re.compile("if"))
THENLEAF = Token("then", re.compile("then"))
ELSELEAF = Token("else", re.compile("else"))
WHILELEAF = Token("while", re.compile("while"))
DOLEAF = Token("do", re.compile("do"))
LPARLEAF = Token("lpar", re.compile(re.escape("(")))
RPARLEAF = Token("rpar", re.compile(re.escape(")")))
LBRACELEAF = Token("lbrace", re.compile(re.escape("{")))
RBRACELEAF = Token("rbrace", re.compile(re.escape("}")))

LOWVAR = ConstantParser(LOWVARLEAF)
HIGHVAR = ConstantParser(HIGHVARLEAF)
INTS = ConstantParser(INTSLEAF)
PLUS = ConstantParser(PLUSLEAF)
MINUS = ConstantParser(MINUSLEAF)
TIMES = ConstantParser(TIMESLEAF)
DIV = ConstantParser(DIVLEAF)
LESS = ConstantParser(LESSLEAF)
LESSEQ = ConstantParser(LESSEQLEAF)
GREATER = ConstantParser(GREATERLEAF)
GREATEREQ = ConstantParser(GREATEREQLEAF)
EQUAL = ConstantParser(EQUALLEAF)
GETS = ConstantParser(GETSLEAF)
SKIP = ConstantParser(SKIPLEAF)
SEMICOLON = ConstantParser(SEMICOLONLEAF)
IF = ConstantParser(IFLEAF)
THEN = ConstantParser(THENLEAF)
ELSE = ConstantParser(ELSELEAF)
WHILE = ConstantParser(WHILELEAF)
DO = ConstantParser(DOLEAF)
LPAR = ConstantParser(LPARLEAF)
RPAR = ConstantParser(RPARLEAF)
LBRACE = ConstantParser(LBRACELEAF)
RBRACE = ConstantParser(RBRACELEAF)


def vars() -> Parser:
    return Choice.of(LOWVAR, HIGHVAR)


def bin_rearrangement(sym: str) -> Rearrangement:
    return Rearrangement(sym, (0, 2))


@rewrite
def boolean_exps() -> Parser:
    return Choice.of(
        Concatenation.of((exps(), LESS, exps()), rearrange=bin_rearrangement("<")),
        Concatenation.of((exps(), LESSEQ, exps()), rearrange=bin_rearrangement("<=")),
        Concatenation.of((exps(), GREATER, exps()), rearrange=bin_rearrangement(">")),
        Concatenation.of((exps(), GREATEREQ, exps()), rearrange=bin_rearrangement(">=")),
        Concatenation.of((exps(), EQUAL, exps()), rearrange=bin_rearrangement("="))
    )


@rewrite
def base_exps() -> Parser:
    return Choice.of(
        vars(),
        INTS,
        Concatenation.of((LPAR, exps(), RPAR), rearrange=Rearrangement("subexpression", (1,)))
    )


@rewrite
def exps() -> Parser:
    return Choice.of(
        base_exps(),
        Concatenation.of((base_exps(), PLUS, exps()), rearrange=bin_rearrangement("+")),
        Concatenation.of((base_exps(), MINUS, exps()), rearrange=bin_rearrangement("-")),
        Concatenation.of((base_exps(), TIMES, exps()), rearrange=bin_rearrangement("*")),
        Concatenation.of((base_exps(), DIV, exps()), rearrange=bin_rearrangement("/")),
    )


@rewrite
def base_commands() -> Parser:
    return Choice.of(
        SKIP,
        Concatenation.of(
            (vars(), GETS, exps(), SEMICOLON),
            rearrange=bin_rearrangement("assign"),
        ),
        Concatenation.of(
            (IF, LPAR, boolean_exps(), RPAR, THEN, LBRACE, commands(), RBRACE, ELSE, LBRACE, commands(), RBRACE),
            rearrange=Rearrangement("ite", (2, 6, 10)),
        ),
        Concatenation.of(
            (WHILE, LPAR, boolean_exps(), RPAR, DO, LBRACE, commands(), RBRACE),
            rearrange=Rearrangement("while", (2, 6)),
        ),
    )


@rewrite
def commands() -> Parser:
    return Choice.of(
        base_commands(),
        Concatenation.of(
            (base_commands(), commands()),
            rearrange=Rearrangement("seq", (0, 1)),
        ),
    )


class SecurityLevel(Enum):
    HIGH = 1
    LOW = 0


@rewrite
def secure_lefthand_vars(t: TreeGrammar, slevel: SecurityLevel) -> TreeGrammar:
    match t:
        case EmptySet():
            return EmptySet()
        case Union(children):
            return Union.of(
                secure_lefthand_vars(c, slevel)
                for c in children
            )
        case Constant(c) if isinstance(c, Token) and c.token_type == "h":
            return t if slevel == SecurityLevel.HIGH else EmptySet()
        case Constant(c) if isinstance(c, Token) and c.token_type == "l":
            return t if slevel == SecurityLevel.LOW else EmptySet()
        case _:
            raise ValueError(f"Unexpected type: {type(t)}")


@rewrite
def secure_exps(t: TreeGrammar, slevel: SecurityLevel) -> TreeGrammar:
    match t:
        case EmptySet():
            return EmptySet()
        case Constant(c) if isinstance(c, Token) and slevel == SecurityLevel.LOW:
            return t if c.token_type in {"l", "int"} else EmptySet()
        case Constant(c) if isinstance(c, Token) and slevel == SecurityLevel.HIGH:
            return t if c.token_type in {"h", "l", "int"} else EmptySet()
        case Application("subexpression", (contents,)):
            return Application.of(
                "subexpression",
                (secure_exps(contents, slevel),),
            )
        case Application(op, (left, right)) if op != "subexpression":
            return Application.of(
                op,
                (
                    secure_exps(left, slevel),
                    secure_exps(right, slevel),
                ),
            )
        case Union(children):
            return Union.of(
                secure_exps(c, slevel)
                for c in children
            )
        case _:
            raise ValueError


@rewrite
def secure_cmds(t: TreeGrammar, slevel: SecurityLevel) -> TreeGrammar:
    match t:
        case EmptySet():
            secure_asts: list[TreeGrammar] = []
        case Constant(_):
            secure_asts = [t]
        case Application("assign", (left, right)):
            secure_asts = [
                Application.of(
                    "assign",
                    (
                        secure_lefthand_vars(left, SecurityLevel.HIGH),
                        right,
                    ),
                )
            ]
            if slevel == SecurityLevel.LOW:
                secure_asts.append(
                    Application.of(
                        "assign",
                        (
                            secure_lefthand_vars(left, SecurityLevel.LOW),
                            secure_exps(right, SecurityLevel.LOW),
                        ),
                    )
                )
        case Application("seq", (left, right)):
            secure_asts = [
                Application.of(
                    "seq",
                    (
                        secure_cmds(left, slevel),
                        secure_cmds(right, slevel),
                    ),
                )
            ]
        case Application("ite", (guard, thencmd, elsecmd)):
            secure_asts = [
                Application.of(
                    "ite",
                    (
                        secure_exps(guard, slevel),
                        secure_cmds(thencmd, slevel),
                        secure_cmds(elsecmd, slevel),
                    ),
                )
            ]
        case Application("while", (guard, body)):
            secure_asts = [
                Application.of(
                    "while",
                    (
                        secure_exps(guard, slevel),
                        secure_cmds(body, slevel),
                    ),
                )
            ]
        case Union(children):
            secure_asts = [
                secure_cmds(c, slevel)
                for c in children
            ]
        case _:
            raise ValueError

    if slevel == SecurityLevel.LOW:
        return Union.of(
            secure_cmds(t, SecurityLevel.HIGH),
            *secure_asts,
        )

    return Union.of(*secure_asts)


lexer_spec = LexerSpec(
    tokens=frozenset(
        {
            LOWVARLEAF,
            HIGHVARLEAF,
            INTSLEAF,
            PLUSLEAF,
            MINUSLEAF,
            TIMESLEAF,
            DIVLEAF,
            LESSLEAF,
            LESSEQLEAF,
            GREATERLEAF,
            GREATEREQLEAF,
            EQUALLEAF,
            GETSLEAF,
            SKIPLEAF,
            SEMICOLONLEAF,
            IFLEAF,
            THENLEAF,
            ELSELEAF,
            WHILELEAF,
            DOLEAF,
            LPARLEAF,
            RPARLEAF,
            LBRACELEAF,
            RBRACELEAF
        }
    ),
    ignore_regex=re.compile(r"\s+"),
)

noninterference_checker = RealizabilityChecker(
    lambda asts: secure_cmds(asts, SecurityLevel.LOW),
    commands(),
    lexer_spec,
)
