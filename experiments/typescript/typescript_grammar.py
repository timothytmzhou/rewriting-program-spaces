import regex as re


from core.parser import *
from core.grammar import *
from lexing.leaves import Token
from lexing.lexing import LexerSpec

# LEXEMES

INTSLEAF = Token("int", re.compile("\\d+(\\.\\d+)?"))
# STRINGSLEAF = Token("str", re.compile("\"\\w*\""))
TRUELEAF = Token("true", re.compile("true"))
FALSELEAF = Token("false", re.compile("false"))
TYPESCRIPTLEAF = Token("typescript", re.compile("typescript"))
IDLEAF = Token(
    "id",
    re.compile(
        "(?!(true|false|number|string|boolean|return|function|let|if|else|typescript)$)"
        + "([a-zA-Z][a-zA-Z0-9_]*)|(Math\\.[a-zA-Z0-9_]+)"  # Math library hack
    )
)

# I'm so sorry this is a necessary speed hack
INTBINOPLEAF = Token("+", re.compile("\\+|\\-|\\*|/|%|(\\*\\*)"))
MINUSLEAF = Token("-", re.compile("\\-"))
COMPARATORLEAF = Token("<", re.compile("(<)|(<=)|(>)|(>=)|(==)|(===)|(!==)|(!=)"))
BOOLEANBINOPLEAF = Token("&&", re.compile("(&&)|(\\|\\|)"))

FUNCARROWLEAF = Token("=>", re.compile("=>"))
DOTLEAF = Token(".", re.compile("\\."))
COLONLEAF = Token(":", re.compile(":"))
QUESTIONMARKLEAF = Token("?", re.compile("\\?"))

NUMBERTYPELEAF = Token("numbertype", re.compile("number"))
BOOLEANTYPELEAF = Token("booltype", re.compile("boolean"))

RETURNLEAF = Token("return", re.compile("return"))
FUNCTIONLEAF = Token("function", re.compile("function"))

GETSLEAF = Token("gets", re.compile("="))
# TODO: When there is time, consider splitting this
GETSPLUSLEAF = Token("+=", re.compile("(\\+=)|(\\*=)|(\\-=)|(/=)|(%=)"))
PLUSPLUSLEAF = Token("++", re.compile("(\\+\\+)|(--)"))
SEMICOLONLEAF = Token(";", re.compile(";"))
COMMALEAF = Token(",", re.compile(","))
# TODO: When there is time, split this and enforce const immutable
LETLEAF = Token("let", re.compile("let"))
CONSTLEAF = Token("const", re.compile("const"))
FORLEAF = Token("for", re.compile("for"))
WHILELEAF = Token("while", re.compile("while"))
IFLEAF = Token("if", re.compile("if"))
ELSELEAF = Token("else", re.compile("else"))
LPARLEAF = Token("lpar", re.compile(re.escape("(")))
RPARLEAF = Token("rpar", re.compile(re.escape(")")))
LBRACELEAF = Token("lbrace", re.compile(re.escape("{")))
RBRACELEAF = Token("rbrace", re.compile(re.escape("}")))

CODEBLOCKLEAF = Token("```", re.compile(r"```"))

INTS = ConstantParser(INTSLEAF)
TRUE = ConstantParser(TRUELEAF)
FALSE = ConstantParser(FALSELEAF)
ID = ConstantParser(IDLEAF)
TYPESCRIPT = ConstantParser(TYPESCRIPTLEAF)

INTBINOP = ConstantParser(INTBINOPLEAF)
MINUS = ConstantParser(MINUSLEAF)
COMPARATOR = ConstantParser(COMPARATORLEAF)
BOOLEANBINOP = ConstantParser(BOOLEANBINOPLEAF)

FUNCARROW = ConstantParser(FUNCARROWLEAF)
DOT = ConstantParser(DOTLEAF)
COLON = ConstantParser(COLONLEAF)
QUESTIONMARK = ConstantParser(QUESTIONMARKLEAF)

NUMBERTYPEPARSER = ConstantParser(NUMBERTYPELEAF)
BOOLEANTYPEPARSER = ConstantParser(BOOLEANTYPELEAF)

RETURN = ConstantParser(RETURNLEAF)
FUNCTION = ConstantParser(FUNCTIONLEAF)

GETS = ConstantParser(GETSLEAF)
GETSPLUS = ConstantParser(GETSPLUSLEAF)
PLUSPLUS = ConstantParser(PLUSPLUSLEAF)
SEMICOLON = ConstantParser(SEMICOLONLEAF)
COMMA = ConstantParser(COMMALEAF)
LET = ConstantParser(LETLEAF)
CONST = ConstantParser(CONSTLEAF)
FOR = ConstantParser(FORLEAF)
WHILE = ConstantParser(WHILELEAF)
IF = ConstantParser(IFLEAF)
ELSE = ConstantParser(ELSELEAF)
LPAR = ConstantParser(LPARLEAF)
RPAR = ConstantParser(RPARLEAF)
LBRACE = ConstantParser(LBRACELEAF)
RBRACE = ConstantParser(RBRACELEAF)

CODEBLOCK = ConstantParser(CODEBLOCKLEAF)


lexer_spec = LexerSpec(
    tokens=frozenset(
        {
            INTSLEAF,
            TRUELEAF,
            FALSELEAF,
            IDLEAF,
            TYPESCRIPTLEAF,
            INTBINOPLEAF,
            MINUSLEAF,
            COMPARATORLEAF,
            BOOLEANBINOPLEAF,
            BOOLEANTYPELEAF,
            FUNCARROWLEAF,
            DOTLEAF,
            COLONLEAF,
            QUESTIONMARKLEAF,
            NUMBERTYPELEAF,
            BOOLEANTYPELEAF,
            RETURNLEAF,
            FUNCTIONLEAF,
            GETSLEAF,
            GETSPLUSLEAF,
            PLUSPLUSLEAF,
            SEMICOLONLEAF,
            COMMALEAF,
            LETLEAF,
            CONSTLEAF,
            FORLEAF,
            WHILELEAF,
            IFLEAF,
            ELSELEAF,
            LPARLEAF,
            RPARLEAF,
            LBRACELEAF,
            RBRACELEAF,
            CODEBLOCKLEAF
        }
    ),
    ignore_regex=re.compile(r"(\s+)|//.*"),
)

BINOP_INT_INT_TO_INT = {"+"}
BINOP_INT_INT_TO_BOOL = {"<"}
BINOP_BOOL_BOOL_TO_BOOL = {"&&"}
BINOP = {*BINOP_INT_INT_TO_INT, *BINOP_INT_INT_TO_BOOL, *BINOP_BOOL_BOOL_TO_BOOL}

# GRAMMAR

# Expression Grammar
# Exp -> Form
#     | Form ? Exp : Exp.

# Form -> Comp
#      | Comp && Comp
#      | Comp || Comp.

# Comp -> Bin
#     | Bin < Bin
#     | Bin == Bin
#     ...

# Bin -> App
#     | App + Bin
#     | App - Bin
#     ...

# App -> Base\_exp
#     | Base\_exp ( )
#     | Base\_exp ( A ).

# Base\_exp -> INT
#     | VAR
#     | ( Exp ).

# Exps -> Exp
#     | Exp , Exps.


# Statement Grammar:
# Statements -> Statement
#             | Statement ; Statements.

# Statement -> Assignment ;
#             | Exp ;
#             | RETURN Exp ;
#             | Block
#             | FUNCTION VAR ( Typed\_id* ) : Type Block
#             | FOR ( Assignment ; Exp ; Reassignment ) Block
#             | WHILE ( Exp ) Block
#             | IF ( Exp ) THEN Statement ELSE Statement
#             | IF ( Exp ) THEN Statement

# Assignment -> LET Typed\_id = Exp
#             | CONST Typed\_id = Exp
#             | Reassignment

# Reassignment -> Typed\_id = Exp
#             | Typed\_id ++
#             | ++ Typed\_id
#             | Typed\_id += Exp

# Typed\_id -> VAR : Type

# Type -> INTTYPE
#     | BOOLTYPE
#     | ( Typed\_id* ) => Type

# Block -> {}
#     | {Statements}


def bin_rearrangement(sym: str) -> Rearrangement:
    return Rearrangement(sym, (0, 2))


def literals() -> Parser:
    return Choice.of(
        INTS,
        # STRINGS,
        TRUE,
        FALSE
    )


def int_binops() -> Parser:
    return Choice.of(
        INTBINOP,
        MINUS
    )


@rewrite
def types() -> Parser:
    return Choice.of(
        NUMBERTYPEPARSER,
        # STRINGTYPEPARSER,
        BOOLEANTYPEPARSER,
        Concatenation.of((LPAR, RPAR, FUNCARROW, types()),
                         rearrange=Rearrangement("0-ary functype", (3,))),
        Concatenation.of((LPAR, params(), RPAR, FUNCARROW, types()),
                         rearrange=Rearrangement("n-ary functype", (1, 4))),
    )


@rewrite
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
def args() -> Parser:
    return Choice.of(
        exps(),
        Concatenation.of(
            (exps(), COMMA, args()),
            rearrange=Rearrangement("arg sequence", (0, 2))
        )
    )


@rewrite
def base_exps() -> Parser:
    return Choice.of(
        literals(),
        ID,
        Concatenation.of((LPAR, exps(), RPAR),
                         rearrange=Rearrangement("grp", (1,))),
        Concatenation.of(base_exps(), LPAR, RPAR,
                         rearrange=Rearrangement("0-ary app", (0,))),
        Concatenation.of(base_exps(), LPAR, args(), RPAR,
                         rearrange=Rearrangement("n-ary app", (0, 2))),
        Concatenation.of(MINUS, base_exps(),
                         rearrange=Rearrangement("unary minus", (1, ))),
    )


@rewrite
def precedence1_exps() -> Parser:
    return Choice.of(
        base_exps(),
        Concatenation.of((base_exps(), int_binops(), precedence1_exps()),
                         rearrange=bin_rearrangement("+"))
    )


@rewrite
def precedence2_exps() -> Parser:
    return Choice.of(
        precedence1_exps(),
        Concatenation.of((precedence1_exps(), COMPARATOR, precedence1_exps()),
                         rearrange=bin_rearrangement("<"))
    )


@rewrite
def precedence3_exps() -> Parser:
    return Choice.of(
        precedence2_exps(),
        Concatenation.of((precedence2_exps(), BOOLEANBINOP, precedence3_exps()),
                         rearrange=bin_rearrangement("&&"))
    )


@rewrite
def exps() -> Parser:
    return Choice.of(
        precedence3_exps(),
        Concatenation.of((precedence3_exps(), QUESTIONMARK, exps(), COLON, exps()),
                         rearrange=Rearrangement("ternary expression", (0, 2, 4)))
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
def assignment() -> Parser:
    return Choice.of(
        Concatenation.of(
            (LET, ID, COLON, types(), GETS, exps()),
            rearrange=Rearrangement("variable declaration", (1, 3, 5)),
        ),
        Concatenation.of(
            (CONST, ID, COLON, types(), GETS, exps()),
            rearrange=Rearrangement("const declaration", (1, 3, 5)),
        ),
        Concatenation.of(
            (LET, ID, GETS, exps()),
            rearrange=Rearrangement("untyped variable declaration", (1, 3)),
        ),
        Concatenation.of(
            (CONST, ID, GETS, exps()),
            rearrange=Rearrangement("untyped const declaration", (1, 3)),
        ),
        reassignment()
    )


@rewrite
def reassignment() -> Parser:
    return Choice.of(
        Concatenation.of(
            (ID, GETS, exps()),
            rearrange=Rearrangement("variable assignment", (0, 2)),
        ),
        Concatenation.of(
            (ID, PLUSPLUS),
            rearrange=Rearrangement("increment", (0, )),
        ),
        Concatenation.of(
            (PLUSPLUS, ID),
            rearrange=Rearrangement("increment", (1, )),
        ),
        Concatenation.of(
            (ID, GETSPLUS, exps()),
            rearrange=Rearrangement("+= assignment", (0, 2)),
        )
    )


@rewrite
def commands() -> Parser:
    return Choice.of(
        Concatenation.of(
            (assignment(), SEMICOLON),
            rearrange=Rearrangement(None, (0,))
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
            (FOR, LPAR,
             assignment(), SEMICOLON, exps(), SEMICOLON, reassignment(),
             RPAR, blocks()),
            rearrange=Rearrangement("for loop", (2, 4, 6, 8))
        ),
        Concatenation.of(
            (WHILE, LPAR, exps(), RPAR, blocks()),
            rearrange=Rearrangement("while loop", (2, 4))
        ),
        Concatenation.of(
            (IF, LPAR, exps(), RPAR, commands(), ELSE, commands()),
            rearrange=Rearrangement("if-then-else", (2, 4, 6))
        ),
        Concatenation.of(
            (IF, LPAR, exps(), RPAR, commands()),
            rearrange=Rearrangement("if-then", (2, 4))
        )
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


@rewrite
def codeblocks() -> Parser:
    return Choice.of(
        Concatenation.of(
            CODEBLOCK, command_seqs(), CODEBLOCK,
            rearrange=Rearrangement(None, (1,))
        ),
        # # Enable or disable "typescript" prefix depending on taste.
        # Concatenation.of(
        #     CODEBLOCK, TYPESCRIPT, command_seqs(), CODEBLOCK,
        #     rearrange=Rearrangement(None, (2,))
        # )
    )
