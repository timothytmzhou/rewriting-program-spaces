import regex as re


from core.parser import *
from core.grammar import *
from lexing.leaves import Token
from lexing.lexing import LexerSpec

# LEXEMES

INTSLEAF = Token("int", re.compile("\\d+"))
STRINGSLEAF = Token("str", re.compile("\"\\w*\""))
TRUELEAF = Token("true", re.compile("true"))
FALSELEAF = Token("false", re.compile("false"))
IDLEAF = Token(
    "id",
    re.compile(
        "(?!(true|false|number|string|boolean|return|function|let|if|else)$)[a-zA-Z]+"
    )
)

PLUSLEAF = Token("+", re.compile("\\+"))
MINUSLEAF = Token("-", re.compile("\\-"))
TIMESLEAF = Token("*", re.compile("\\*"))
DIVLEAF = Token("/", re.compile("/"))
MODLEAF = Token("+", re.compile("%"))
LESSLEAF = Token("<", re.compile("<"))
LESSEQLEAF = Token("<=", re.compile("<="))
GREATERLEAF = Token(">", re.compile(">"))
GREATEREQLEAF = Token(">=", re.compile(">="))
EQUALLEAF = Token("==", re.compile("=="))
NOTEQUALLEAF = Token("!==", re.compile("((!==)|(!=))"))

FUNCARROWLEAF = Token("=>", re.compile("=>"))
DOTLEAF = Token(".", re.compile("\\."))
COLONLEAF = Token(":", re.compile(":"))

NUMBERTYPELEAF = Token("numbertype", re.compile("number"))
STRINGTYPELEAF = Token("stringtype", re.compile("string"))
BOOLEANTYPELEAF = Token("booltype", re.compile("boolean"))

RETURNLEAF = Token("return", re.compile("return"))
FUNCTIONLEAF = Token("function", re.compile("function"))

GETSLEAF = Token("gets", re.compile("="))
SEMICOLONLEAF = Token(";", re.compile(";"))
COMMALEAF = Token(",", re.compile(","))
LETLEAF = Token("let", re.compile("let"))
IFLEAF = Token("if", re.compile("if"))
ELSELEAF = Token("else", re.compile("else"))
LPARLEAF = Token("lpar", re.compile(re.escape("(")))
RPARLEAF = Token("rpar", re.compile(re.escape(")")))
LBRACELEAF = Token("lbrace", re.compile(re.escape("{")))
RBRACELEAF = Token("rbrace", re.compile(re.escape("}")))

INTS = ConstantParser(INTSLEAF)
STRINGS = ConstantParser(STRINGSLEAF)
TRUE = ConstantParser(TRUELEAF)
FALSE = ConstantParser(FALSELEAF)
ID = ConstantParser(IDLEAF)

PLUS = ConstantParser(PLUSLEAF)
MINUS = ConstantParser(MINUSLEAF)
TIMES = ConstantParser(TIMESLEAF)
DIV = ConstantParser(DIVLEAF)
MOD = ConstantParser(MODLEAF)
LESS = ConstantParser(LESSLEAF)
LESSEQ = ConstantParser(LESSEQLEAF)
GREATER = ConstantParser(GREATERLEAF)
GREATEREQ = ConstantParser(GREATEREQLEAF)
EQUAL = ConstantParser(EQUALLEAF)
NOTEQUAL = ConstantParser(NOTEQUALLEAF)

FUNCARROW = ConstantParser(FUNCARROWLEAF)
DOT = ConstantParser(DOTLEAF)
COLON = ConstantParser(COLONLEAF)

NUMBERTYPEPARSER = ConstantParser(NUMBERTYPELEAF)
STRINGTYPEPARSER = ConstantParser(STRINGTYPELEAF)
BOOLEANTYPEPARSER = ConstantParser(BOOLEANTYPELEAF)

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


lexer_spec = LexerSpec(
    tokens=frozenset(
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
            MODLEAF,
            LESSLEAF,
            LESSEQLEAF,
            GREATERLEAF,
            GREATEREQLEAF,
            EQUALLEAF,
            NOTEQUALLEAF,
            FUNCARROWLEAF,
            DOTLEAF,
            COLONLEAF,
            NUMBERTYPELEAF,
            STRINGTYPELEAF,
            BOOLEANTYPELEAF,
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
    ignore_regex=re.compile(r"(\s+)|//.*"),
)


# GRAMMAR


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
        NUMBERTYPEPARSER,
        STRINGTYPEPARSER,
        BOOLEANTYPEPARSER,
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
        # Concatenation.of((LPAR, RPAR, FUNCARROW, exps()),
        #                  rearrange=Rearrangement("0-ary lambda", (3,))),
        # Concatenation.of((LPAR, params(), RPAR, FUNCARROW, exps()),
        #                  rearrange=Rearrangement("n-ary lambda", (1, 4))),
        Concatenation.of((LPAR, exps(), RPAR),
                         rearrange=Rearrangement("grp", (1,))),
        Concatenation.of(exps(), LPAR, RPAR,
                         rearrange=Rearrangement("0-ary app", (0,))),
        Concatenation.of(exps(), LPAR, args(), RPAR,
                         rearrange=Rearrangement("n-ary app", (0, 2))),
        # Concatenation.of(exps(), DOT, ID,
        #                  rearrange=Rearrangement("dot access", (0, 2)))
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
def numeric_bin_exps() -> Parser:
    return Choice.of(
        Concatenation.of((base_exps(), PLUS, non_comparators()),
                         rearrange=bin_rearrangement("+")),
        Concatenation.of((base_exps(), MINUS, non_comparators()),
                         rearrange=bin_rearrangement("-")),
        Concatenation.of((base_exps(), TIMES, non_comparators()),
                         rearrange=bin_rearrangement("*")),
        Concatenation.of((base_exps(), DIV, non_comparators()),
                         rearrange=bin_rearrangement("/")),
        Concatenation.of((base_exps(), MOD, non_comparators()),
                         rearrange=bin_rearrangement("%"))
    )


@rewrite
def non_comparators() -> Parser:
    return Choice.of(
        numeric_bin_exps(),
        base_exps()
    )


@rewrite
def boolean_bin_exps() -> Parser:
    return Choice.of(
        Concatenation.of((non_comparators(), LESS, non_comparators()),
                         rearrange=bin_rearrangement("<")),
        Concatenation.of((non_comparators(), LESSEQ, non_comparators()),
                         rearrange=bin_rearrangement("<=")),
        Concatenation.of((non_comparators(), GREATER, non_comparators()),
                         rearrange=bin_rearrangement(">")),
        Concatenation.of((non_comparators(), GREATEREQ, non_comparators()),
                         rearrange=bin_rearrangement(">=")),
        Concatenation.of((non_comparators(), EQUAL, non_comparators()),
                         rearrange=bin_rearrangement("==")),
        Concatenation.of((non_comparators(), NOTEQUAL, non_comparators()),
                         rearrange=bin_rearrangement("!=="))
    )


@rewrite
def exps() -> Parser:
    return Choice.of(
        boolean_bin_exps(),
        numeric_bin_exps(),
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
        # Concatenation.of(
        #     (LET, ID, COLON, types(), GETS, exps(), SEMICOLON),
        #     rearrange=Rearrangement("variable declaration", (1, 3, 5)),
        # ),
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
        # Concatenation.of(
        #     (IF, LPAR, exps(), RPAR, commands(), ELSE, commands()),
        #     rearrange=Rearrangement("if-then-else", (2, 4, 6))
        # )
    )


@rewrite
def command_seqs() -> Parser:
    return Choice.of(
        commands(),
        Concatenation.of(
            (commands(), command_seqs()),
            rearrange=Rearrangement("command seq", (0, 1)),
        ),
    )
