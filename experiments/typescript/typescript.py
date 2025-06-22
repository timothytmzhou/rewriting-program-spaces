import regex as re

from core.parser import *
from core.grammar import *
from lexing.leaves import RegexLeaf
from lexing.lexing import LexerSpec
# from runllm.constrained_decoding import RealizabilityChecker


# SYNTAX
INTSLEAF = RegexLeaf("int", re.compile("\\d+"))
STRINGSLEAF = RegexLeaf("str", re.compile("\"\\w*\""))
TRUELEAF = RegexLeaf("true", re.compile("true"))
FALSELEAF = RegexLeaf("false", re.compile("false"))
IDLEAF = RegexLeaf(
    "id",
    re.compile(
        "(?!(true|false|number|string|boolean|return|function|let|if|else)$)\\w+"
    )
)

PLUSLEAF = RegexLeaf("+", re.compile("\\+"))
MINUSLEAF = RegexLeaf("-", re.compile("\\-"))
TIMESLEAF = RegexLeaf("*", re.compile("\\*"))
DIVLEAF = RegexLeaf("/", re.compile("/"))
LESSLEAF = RegexLeaf("<", re.compile("<"))
LESSEQLEAF = RegexLeaf("<=", re.compile("<="))
GREATERLEAF = RegexLeaf(">", re.compile(">"))
GREATEREQLEAF = RegexLeaf(">=", re.compile(">="))
EQUALLEAF = RegexLeaf("==", re.compile("=="))

FUNCARROWLEAF = RegexLeaf("=>", re.compile("=>"))
DOTLEAF = RegexLeaf(".", re.compile("\\."))
COLONLEAF = RegexLeaf(":", re.compile(":"))

NUMTYPELEAF = RegexLeaf("numbertype", re.compile("number"))
STRINGTYPELEAF = RegexLeaf("stringtype", re.compile("string"))
BOOLTYPELEAF = RegexLeaf("booltype", re.compile("boolean"))

RETURNLEAF = RegexLeaf("return", re.compile("return"))
FUNCTIONLEAF = RegexLeaf("function", re.compile("function"))

GETSLEAF = RegexLeaf("gets", re.compile("="))
SEMICOLONLEAF = RegexLeaf(";", re.compile(";"))
COMMALEAF = RegexLeaf(",", re.compile(","))
LETLEAF = RegexLeaf("let", re.compile("let"))
IFLEAF = RegexLeaf("if", re.compile("if"))
ELSELEAF = RegexLeaf("else", re.compile("else"))
LPARLEAF = RegexLeaf("lpar", re.compile(re.escape("(")))
RPARLEAF = RegexLeaf("rpar", re.compile(re.escape(")")))
LBRACELEAF = RegexLeaf("lbrace", re.compile(re.escape("{")))
RBRACELEAF = RegexLeaf("rbrace", re.compile(re.escape("}")))

INTS = ConstantParser(INTSLEAF)
STRINGS = ConstantParser(STRINGSLEAF)
TRUE = ConstantParser(TRUELEAF)
FALSE = ConstantParser(FALSELEAF)
ID = ConstantParser(IDLEAF)

PLUS = ConstantParser(PLUSLEAF)
MINUS = ConstantParser(MINUSLEAF)
TIMES = ConstantParser(TIMESLEAF)
DIV = ConstantParser(DIVLEAF)
LESS = ConstantParser(LESSLEAF)
LESSEQ = ConstantParser(LESSEQLEAF)
GREATER = ConstantParser(GREATERLEAF)
GREATEREQ = ConstantParser(GREATEREQLEAF)
EQUAL = ConstantParser(EQUALLEAF)

FUNCARROW = ConstantParser(FUNCARROWLEAF)
DOT = ConstantParser(DOTLEAF)
COLON = ConstantParser(COLONLEAF)

NUMTYPE = ConstantParser(NUMTYPELEAF)
STRINGTYPE = ConstantParser(STRINGTYPELEAF)
BOOLTYPE = ConstantParser(BOOLTYPELEAF)

RETURN = ConstantParser(RETURNLEAF)
FUNCTION = ConstantParser(FUNCTIONLEAF)

GETS = ConstantParser(GETSLEAF)
SEMICOLON = ConstantParser(SEMICOLONLEAF)
COMMA = ConstantParser(COMMALEAF)
LET = ConstantParser(LETLEAF)
IF = ConstantParser(IFLEAF)
ELSE = ConstantParser(ELSELEAF)
LPAR = ConstantParser(LPARLEAF)
RPAR = ConstantParser(RPARLEAF)
LBRACE = ConstantParser(LBRACELEAF)
RBRACE = ConstantParser(RBRACELEAF)


def bin_rearrangement(sym: str) -> Rearrangement:
    return Rearrangement(sym, (0, 2))


def literals() -> Parser:
    return Choice.of(
        INTS,
        STRINGS,
        TRUE,
        FALSE
    )


@rewrite
def type_seqs() -> Parser:
    return Choice.of(
        types(),
        Concatenation.of(
            (types(), COMMA, type_seqs()),
            rearrange=Rearrangement("type sequence", (0, 2))
        )
    )


@rewrite
def types() -> Parser:
    return Choice.of(
        NUMTYPE,
        STRINGTYPE,
        BOOLTYPE,
        Concatenation.of((LPAR, RPAR, FUNCARROW, types()),
                         rearrange=Rearrangement("0-ary functype", (3,))),
        Concatenation.of((LPAR, type_seqs(), RPAR, FUNCARROW, types()),
                         rearrange=Rearrangement("n-ary functype", (1, 4))),
    )


def typed_id() -> Parser:
    return Concatenation.of(
        (ID, COLON, types()),
        rearrange=Rearrangement("typed_id", (0, 2))
    )


@rewrite
def params() -> Parser:
    return Choice.of(
        typed_id(),
        Concatenation.of(
            (typed_id(), COMMA, params()),
            rearrange=Rearrangement("param sequence", (0, 2))
        )
    )


@rewrite
def base_exps() -> Parser:
    return Choice.of(
        literals(),
        ID,
        Concatenation.of((LPAR, RPAR, FUNCARROW, exps()),
                         rearrange=Rearrangement("0-ary lambda", (3,))),
        Concatenation.of((LPAR, params(), RPAR, FUNCARROW, exps()),
                         rearrange=Rearrangement("n-ary lambda", (1, 4))),
        Concatenation.of((LPAR, exps(), RPAR),
                         rearrange=Rearrangement("grp", (1,))),
        Concatenation.of(exps(), LPAR, RPAR,
                         rearrange=Rearrangement("0-ary app", (0,))),
        Concatenation.of(exps(), LPAR, args(), RPAR,
                         rearrange=Rearrangement("n-ary app", (0, 2))),
        Concatenation.of(exps(), DOT, ID,
                         rearrange=Rearrangement("dot access", (0, 2)))
    )


@rewrite
def args() -> Parser:
    return Choice.of(
        exps(),
        Concatenation.of(
            (exps(), COMMA, args()),
            rearrange=Rearrangement("arg sequence", (0, 2))
        )
    )


@rewrite
def bin_exps() -> Parser:
    return Choice.of(
        Concatenation.of((base_exps(), PLUS, exps()),
                         rearrange=bin_rearrangement("+")),
        Concatenation.of((base_exps(), MINUS, exps()),
                         rearrange=bin_rearrangement("-")),
        Concatenation.of((base_exps(), TIMES, exps()),
                         rearrange=bin_rearrangement("*")),
        Concatenation.of((base_exps(), DIV, exps()),
                         rearrange=bin_rearrangement("/")),
        Concatenation.of((base_exps(), LESS, exps()),
                         rearrange=bin_rearrangement("<")),
        Concatenation.of((base_exps(), LESSEQ, exps()),
                         rearrange=bin_rearrangement("<=")),
        Concatenation.of((base_exps(), GREATER, exps()),
                         rearrange=bin_rearrangement(">")),
        Concatenation.of((base_exps(), GREATEREQ, exps()),
                         rearrange=bin_rearrangement(">=")),
        Concatenation.of((base_exps(), EQUAL, exps()),
                         rearrange=bin_rearrangement("=="))
    )


@rewrite
def exps() -> Parser:
    return Choice.of(
        bin_exps(),
        base_exps(),
    )


@rewrite
def blocks() -> Parser:
    return Choice.of(
        Concatenation.of(
            (LBRACE, RBRACE),
            rearrange=Rearrangement("empty block", tuple()),
        ),
        Concatenation.of(
            (LBRACE, command_seqs(), RBRACE),
            rearrange=Rearrangement("nonempty block", (1,)),
        )
    )


@rewrite
def commands() -> Parser:
    return Choice.of(
        Concatenation.of(
            (LET, ID, COLON, types(), GETS, exps(), SEMICOLON),
            rearrange=Rearrangement("variable declaration", (1, 3, 5)),
        ),
        Concatenation.of(
            (exps(), SEMICOLON),
            rearrange=Rearrangement("expression statement", (0,)),
        ),
        Concatenation.of(
            (RETURN, exps(), SEMICOLON),
            rearrange=Rearrangement("return statement", (1,)),
        ),
        blocks(),
        Concatenation.of(
            (FUNCTION, ID, LPAR, RPAR, COLON, types(), blocks()),
            rearrange=Rearrangement("0-ary func decl", (1, 5, 6))
        ),
        Concatenation.of(
            (FUNCTION, ID, LPAR, params(), RPAR, COLON, types(), blocks()),
            rearrange=Rearrangement("n-ary func decl", (1, 3, 6, 7))
        ),
        Concatenation.of(
            (IF, LPAR, exps(), RPAR, commands(), ELSE, commands()),
            rearrange=Rearrangement("n-ary func decl", (2, 4, 6))
        )
    )


@rewrite
def command_seqs() -> Parser:
    return Choice.of(
        commands(),
        Concatenation.of(
            (commands(), command_seqs()),
            rearrange=Rearrangement("seq", (0, 1)),
        ),
    )


lexer_spec = LexerSpec(
    tok2regex=frozenset(
        {
            INTSLEAF,
            STRINGSLEAF,
            TRUELEAF,
            FALSELEAF,
            IDLEAF,
            PLUSLEAF,
            MINUSLEAF,
            TIMESLEAF,
            DIVLEAF,
            LESSLEAF,
            LESSEQLEAF,
            GREATERLEAF,
            GREATEREQLEAF,
            EQUALLEAF,
            FUNCARROWLEAF,
            DOTLEAF,
            COLONLEAF,
            NUMTYPELEAF,
            STRINGTYPELEAF,
            BOOLTYPELEAF,
            RETURNLEAF,
            FUNCTIONLEAF,
            GETSLEAF,
            SEMICOLONLEAF,
            COMMALEAF,
            LETLEAF,
            IFLEAF,
            ELSELEAF,
            LPARLEAF,
            RPARLEAF,
            LBRACELEAF,
            RBRACELEAF
        }
    ),
    ignore_regex=re.compile(r"\s+"),
)
