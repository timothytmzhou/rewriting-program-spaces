import greenery as grn
from enum import Enum

from core.parser import *
from core.grammar import *
from lexing.leaves import RegexLeaf
from lexing.lexing import LexerSpec
from runllm.constrained_decoding import RealizabilityChecker
from tests.utils import reset


# SYNTAX
LOWVARLEAF = RegexLeaf("l", grn.parse("l"))
HIGHVARLEAF = RegexLeaf("h", grn.parse("h"))
INTSLEAF = RegexLeaf("int", grn.parse("0|([1-9][0-9]*)"))
PLUSLEAF = RegexLeaf("+", grn.parse("\\+"))
LESSLEAF = RegexLeaf("<", grn.parse("<"))
LESSEQLEAF = RegexLeaf("<=", grn.parse("<="))
GREATERLEAF = RegexLeaf(">", grn.parse(">"))
GREATEREQLEAF = RegexLeaf(">=", grn.parse(">="))
EQUALLEAF = RegexLeaf("=", grn.parse("="))
GETSLEAF = RegexLeaf(":=", grn.parse(":="))
SKIPLEAF = RegexLeaf("skip", grn.parse("skip"))
SEMICOLONLEAF = RegexLeaf(";", grn.parse(";"))
IFLEAF = RegexLeaf("if", grn.parse("if"))
THENLEAF = RegexLeaf("then", grn.parse("then"))
ELSELEAF = RegexLeaf("else", grn.parse("else"))
WHILELEAF = RegexLeaf("while", grn.parse("while"))
DOLEAF = RegexLeaf("do", grn.parse("do"))

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


def bin_rearr(sym: str) -> Rearrangement:
    return Rearrangement(sym, (0, 2))


@rewrite
def exps() -> Parser:
    return Choice.of(
        vars(),
        INTS,
        Concatenation.of((exps(), PLUS, exps()), bin_rearr("+")),
        Concatenation.of((exps(), LESS, exps()), bin_rearr("<")),
        Concatenation.of((exps(), LESSEQ, exps()), bin_rearr("<=")),
        Concatenation.of((exps(), GREATER, exps()), bin_rearr(">")),
        Concatenation.of((exps(), GREATEREQ, exps()), bin_rearr(">=")),
        Concatenation.of((exps(), EQUAL, exps()), bin_rearr("="))
    )


@rewrite
def commands() -> Parser:
    return Choice.of(
        SKIP,
        Concatenation.of((vars(), GETS, exps()), bin_rearr(":=")),
        Concatenation.of((commands(), SEMICOLON, commands()), bin_rearr(";")),
        Concatenation.of(
            (IF, exps(), THEN, commands(), ELSE, commands()), Rearrangement("ite", (1, 3, 5))
        ),
        Concatenation.of((WHILE, exps(), DO, commands()), Rearrangement("while", (1, 3)))
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
            return Application(op, (secure_exps(left, slevel), secure_exps(right, slevel)))
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
                Application("assign", (secure_lefthand_vars(left, SecurityLevel.HIGH), right))
            ]
            if slevel == SecurityLevel.LOW:
                secure_asts.append(
                    Application(
                        "assign",
                        (
                            secure_lefthand_vars(left, SecurityLevel.LOW),
                            secure_exps(right, SecurityLevel.LOW),
                        ),
                    )
                )
        case Application("seq", (left, right)):
            secure_asts = [
                Application("seq", (secure_cmds(left, slevel), secure_cmds(right, slevel)))
            ]
        case Application("ite", (guard, thencmd, elsecmd)):
            secure_asts = [
                Application(
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
                Application("while", (secure_exps(guard, slevel), secure_cmds(body, slevel)))
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
    ignore_regex=grn.parse(r"\s+"),
)


@reset
def test_noninterference():
    noninterference_checker = RealizabilityChecker(
        lambda asts: secure_cmds(asts, SecurityLevel.LOW), commands(), lexer_spec
    )
    assert noninterference_checker.realizable("")
    assert noninterference_checker.realizable("skip")
    assert noninterference_checker.realizable("h := l; skip")
    assert not noninterference_checker.realizable("l := h")
    assert noninterference_checker.realizable("l := l + 634;")
    assert not noninterference_checker.realizable("l := l + h")
    assert noninterference_checker.realizable("if l = 10 then h := 1 else l := 1")
    assert not noninterference_checker.realizable("if h = 10 then h := 1 else l := 1")
    assert noninterference_checker.realizable("while h < 10 do h := h + 1")
    assert not noninterference_checker.realizable("while h + l < 10 do l := l + 1")
