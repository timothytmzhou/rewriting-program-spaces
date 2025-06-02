import regex as re
from enum import Enum

from core.parser import *
from core.grammar import *
from lexing.leaves import RegexLeaf
from lexing.lexing import LexerSpec
from runllm.constrained_decoding import RealizabilityChecker


# SYNTAX
LOWVARLEAF = RegexLeaf("l", re.compile("l"))
HIGHVARLEAF = RegexLeaf("h", re.compile("h"))
INTSLEAF = RegexLeaf("int", re.compile("0|([1-9][0-9]*)"))
PLUSLEAF = RegexLeaf("+", re.compile("\\+"))
LESSLEAF = RegexLeaf("<", re.compile("<"))
LESSEQLEAF = RegexLeaf("<=", re.compile("<="))
GREATERLEAF = RegexLeaf(">", re.compile(">"))
GREATEREQLEAF = RegexLeaf(">=", re.compile(">="))
EQUALLEAF = RegexLeaf("=", re.compile("="))
GETSLEAF = RegexLeaf(":=", re.compile(":="))
SKIPLEAF = RegexLeaf("skip", re.compile("skip"))
SEMICOLONLEAF = RegexLeaf(";", re.compile(";"))
IFLEAF = RegexLeaf("if", re.compile("if"))
THENLEAF = RegexLeaf("then", re.compile("then"))
ELSELEAF = RegexLeaf("else", re.compile("else"))
WHILELEAF = RegexLeaf("while", re.compile("while"))
DOLEAF = RegexLeaf("do", re.compile("do"))

LOWVAR = ConstantParser(LOWVARLEAF)
HIGHVAR = ConstantParser(HIGHVARLEAF)
INTS = ConstantParser(INTSLEAF)
PLUS = ConstantParser(PLUSLEAF)
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


def vars() -> Parser:
    return Choice.of(LOWVAR, HIGHVAR)


def bin_rearrangement(sym: str) -> Rearrangement:
    return Rearrangement(sym, (0, 2))


@rewrite
def exps() -> Parser:
    return Choice.of(
        vars(),
        INTS,
        Concatenation.of((exps(), PLUS, exps()), rearrange=bin_rearrangement("+")),
        Concatenation.of((exps(), LESS, exps()), rearrange=bin_rearrangement("<")),
        Concatenation.of((exps(), LESSEQ, exps()), rearrange=bin_rearrangement("<=")),
        Concatenation.of((exps(), GREATER, exps()), rearrange=bin_rearrangement(">")),
        Concatenation.of((exps(), GREATEREQ, exps()), rearrange=bin_rearrangement(">=")),
        Concatenation.of((exps(), EQUAL, exps()), rearrange=bin_rearrangement("="))
    )


@rewrite
def commands() -> Parser:
    return Choice.of(
        SKIP,
        Concatenation.of((vars(), GETS, exps()), rearrange=bin_rearrangement("assign")),
        Concatenation.of((commands(), SEMICOLON, commands()),
                         rearrange=bin_rearrangement("seq")),
        Concatenation.of(
            (IF, exps(), THEN, commands(), ELSE, commands()),
            rearrange=Rearrangement("ite", (1, 3, 5))
        ),
        Concatenation.of((WHILE, exps(), DO, commands()),
                         rearrange=Rearrangement("while", (1, 3)))
    )


# CONSTRAINTS
class SecurityLevel(Enum):
    HIGH = 1
    LOW = 0


@rewrite
def secure_lefthand_vars(t: TreeGrammar, slevel: SecurityLevel) -> TreeGrammar:
    # LHS variables
    match t:
        case EmptySet():
            return EmptySet()
        case Union(children):
            return Union.of(secure_lefthand_vars(c, slevel) for c in children)
        case Constant(c) if isinstance(c, RegexLeaf) and c.sort == "h":
            return t if slevel == SecurityLevel.HIGH else EmptySet()
        case Constant(c) if isinstance(c, RegexLeaf) and c.sort == "l":
            return t if slevel == SecurityLevel.LOW else EmptySet()
        case _:
            raise ValueError(f"Unexpected type: {type(t)}")


@rewrite
def secure_exps(t: TreeGrammar, slevel: SecurityLevel) -> TreeGrammar:
    # Expressions
    match t:
        case EmptySet():
            return EmptySet()
        case Constant(c) if isinstance(c, RegexLeaf) and slevel == SecurityLevel.LOW:
            return t if c.sort in {"l", "int"} else EmptySet()
        case Constant(c) if isinstance(c, RegexLeaf) and slevel == SecurityLevel.HIGH:
            return t if c.sort in {"h", "l", "int"} else EmptySet()
        case Application(op, (left, right)):
            return Application.of(op, (secure_exps(left, slevel), secure_exps(right, slevel)))
        case Union(children):
            return Union.of(secure_exps(c, slevel) for c in children)
        case _:
            raise ValueError


@rewrite
def secure_cmds(t: TreeGrammar, slevel: SecurityLevel) -> TreeGrammar:
    # Commands
    secure_asts: list[TreeGrammar]
    match t:
        case EmptySet():
            secure_asts = []
        case Constant(_):
            secure_asts = [t]
        case Application("assign", (left, right)):
            secure_asts = [
                Application.of("assign", (secure_lefthand_vars(left, SecurityLevel.HIGH), right))
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
                Application.of("seq", (secure_cmds(left, slevel), secure_cmds(right, slevel)))
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
                Application.of("while", (secure_exps(guard, slevel), secure_cmds(body, slevel)))
            ]
        case Union(children):
            secure_asts = [secure_cmds(c, slevel) for c in children]
        case _:
            raise ValueError
    if slevel == SecurityLevel.LOW:
        return Union.of(secure_cmds(t, SecurityLevel.HIGH), *secure_asts)
    return Union.of(*secure_asts)


# PARSING AND CHECKING STRINGS
lexer_spec = LexerSpec(
    tok2regex=frozenset(
        {
            LOWVARLEAF,
            HIGHVARLEAF,
            INTSLEAF,
            PLUSLEAF,
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
        }
    ),
    ignore_regex=re.compile(r"\s+"),
)


noninterference_checker = RealizabilityChecker(
    lambda asts: secure_cmds(asts, SecurityLevel.LOW), commands(), lexer_spec
)
