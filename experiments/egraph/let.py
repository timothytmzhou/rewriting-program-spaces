import regex
from enum import Enum
from core.rewrite import rewrite
from core.parser import *
from core.grammar import expand_tree_grammar
from lexing.leaves import Token
from lexing.lexing import LexerSpec
from .egraph import EGraph, in_egraph
from functools import lru_cache


TokenTypes = Enum("TokenTypes", "ID INT LPAR RPAR LET EQUALS IN PLUS TIMES SUB DIV CODEBLOCK")


def make_token(name, pattern: str) -> Token:
    return Token(TokenTypes[name], regex.compile(pattern))


ID = make_token("ID", r"(?!(let|in)$)[a-zA-Z_][a-zA-Z0-9_]*")
INT = make_token("INT", r"\d+")
LPAR = make_token("LPAR", r"\(")
RPAR = make_token("RPAR", r"\)")
LET = make_token("LET", r"let")
EQUALS = make_token("EQUALS", r"=")
IN = make_token("IN", r"in")
PLUS = make_token("PLUS", r"\+")
TIMES = make_token("TIMES", r"\*")
SUB = make_token("SUB", r"-")
DIV = make_token("DIV", r"/")
CODEBLOCK = make_token("CODEBLOCK", r"```")

let_lexer_spec = LexerSpec(
    tokens=frozenset({ID, INT, LPAR, RPAR, LET, EQUALS, IN, PLUS, TIMES, SUB, DIV, CODEBLOCK}),
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
def NonNegAtom() -> Parser:
    return Choice.of(
        Id(),
        Num(),
        Concatenation.of(
            ConstantParser(LPAR), Let(), ConstantParser(RPAR),
            rearrange=Rearrangement(None, (1,))
        )
    )


@rewrite
def Atom() -> Parser:
    return Choice.of(
        NonNegAtom(),
        Concatenation.of(
            ConstantParser(SUB), Atom(),
            rearrange=Rearrangement("Neg", (1,))
        )
    )


@rewrite
def App() -> Parser:
    return Choice.of(
        Atom(),
        Concatenation.of(App(), NonNegAtom(),
                         rearrange=Rearrangement("App", (0, 1)))
    )


@rewrite
def Mul() -> Parser:
    return Choice.of(
        App(),
        Concatenation.of(Mul(), ConstantParser(TIMES), App(),
                         rearrange=Rearrangement("Mul", (0, 2))),
        Concatenation.of(Mul(), ConstantParser(DIV), App(),
                         rearrange=Rearrangement("Div", (0, 2)))
    )


@rewrite
def Add() -> Parser:
    return Choice.of(
        Mul(),
        Concatenation.of(Add(), ConstantParser(PLUS), Mul(),
                         rearrange=Rearrangement("Add", (0, 2))),
        Concatenation.of(Add(), ConstantParser(SUB), Mul(),
                         rearrange=Rearrangement("Sub", (0, 2)))
    )


@rewrite
def Let() -> Parser:
    return Choice.of(
        Add(),
        Concatenation.of(
            ConstantParser(LET), Id(), ConstantParser(EQUALS), Add(),
            ConstantParser(IN), Let(),
            rearrange=Rearrangement("Let", (1, 3, 5))
        )
    )


@rewrite
def CodeBlock() -> Parser:
    return Concatenation.of(
        ConstantParser(CODEBLOCK), Let(), ConstantParser(CODEBLOCK),
        rearrange=Rearrangement(None, (1,))
    )


def expr_to_egglog(expr: TreeGrammar) -> str:
    match expr:
        case Application("Var", (Constant(Token(prefix=name)),)):
            return f'(Var "{name}")'
        case Application("Num", (Constant(Token(prefix=name)),)):
            return f"(Num {name})"
        case Application(f, children):
            egglog_children = " ".join(expr_to_egglog(child)
                                       for child in children)
            return f"({f} {egglog_children})"
        case _:
            raise ValueError(f"Unable to process expression: {expr}")


@lru_cache(maxsize=None)
def update_egraph(
    egraph: EGraph,
    binding: TreeGrammar,
    expr: TreeGrammar,
    saturation_depth=100
) -> EGraph:
    new_egraph = EGraph(record=True)
    ran_commands = egraph.commands()
    assert ran_commands is not None, "got EGraph with record=False"
    lines = [
        line for line in ran_commands.splitlines()
        if not line.startswith("(run-schedule")
    ]
    new_egraph.run_program(*new_egraph.parse_program("\n".join(lines)))

    # This fully unrolls the tree grammars so we can use them like normal data.
    binding = expand_tree_grammar(binding)
    expr = expand_tree_grammar(expr)

    # build egglog rewrite
    binding_egglog = expr_to_egglog(binding)
    expr_egglog = expr_to_egglog(expr)
    rewrite_str = f"(rewrite {expr_egglog} {binding_egglog})"

    # run the commands and saturate the egraph
    saturate_str = f"(run {saturation_depth})"
    new_commands = new_egraph.parse_program(rewrite_str + "\n" + saturate_str)
    new_egraph.run_program(*new_commands)
    return new_egraph


@rewrite
def let_equivalence(
    egraph: EGraph,
    t: TreeGrammar,
    used_names: Optional[frozenset[str]] = None
) -> TreeGrammar:
    if used_names is None:
        used_names = frozenset()
    match t:
        case EmptySet():
            return EmptySet()
        case Union(children):
            return Union.of(let_equivalence(egraph, child, used_names)
                            for child in children)
        case Application("Let", (binding, expr1, expr2), focus):
            match expand_tree_grammar(binding):
                case Application("Var", (Constant(Token(prefix=name, is_complete=True)),)):
                    if name in used_names:
                        return EmptySet()
                    used_names = used_names.union({name})
            if focus >= 2:
                updated = update_egraph(egraph, binding, expr1)
                return let_equivalence(updated, expr2, used_names)
            return t
        case _:
            return in_egraph(egraph)(t)
