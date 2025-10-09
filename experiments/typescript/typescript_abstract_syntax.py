from dataclasses import dataclass
from importlib.resources import files
from core.grammar import Application, TreeGrammar, Zeroary, Unary, Binary, Ternary
from core.lark.from_lark import parse_attribute_grammar
from llm.realizability import RealizabilityChecker

# # # Leaves # # #


class Var(Unary): ...


class BooleanConst(Zeroary): ...


class IntConst(Unary): ...


# # # Types and Helpers # # #

class NumberTypeLit(Zeroary): ...


class BooleanTypeLit(Zeroary): ...


class ZaryFuncType(Unary): ...


class NaryFuncType(Binary): ...


class TypedId(Binary): ...


class ParamSeq(Binary): ...


class ArgSeq(Binary): ...


# # # Expressions # # #


class Group(Unary): ...


class ZaryFuncApp(Unary): ...


class NaryFuncApp(Binary): ...


class UnaryMinus(Binary): ...


class Binop(Ternary): ...


class IntBinop(Binop): ...


class IntComparison(Binop): ...


class BooleanBinop(Binop): ...


@dataclass(frozen=True)
class TernaryExpression(Application):
    condition: TreeGrammar
    then_branch: TreeGrammar
    else_branch: TreeGrammar


# # # Commands # # #


class EmptyBlock(Zeroary): ...


class NonemptyBlock(Unary): ...


@dataclass(frozen=True)
class TypedDecl(Application):
    var: TreeGrammar
    type: TreeGrammar
    exp: TreeGrammar


class TypedLetDecl(TypedDecl): ...


class TypedConstDecl(TypedDecl): ...


@dataclass(frozen=True)
class UntypedDecl(Application):
    var: TreeGrammar
    exp: TreeGrammar


class UntypedLetDecl(UntypedDecl): ...


class UntypedConstDecl(UntypedDecl): ...


class VarAssignment(Binary): ...


class VarIncrement(Binary): ...


class VarPreIncrement(Binary): ...


class PlusEqualsAssignment(Ternary): ...


class ExpressionStatement(Unary): ...


class ReturnStatement(Unary): ...


@dataclass(frozen=True)
class ZaryFuncDecl(Application):
    name: TreeGrammar
    return_type: TreeGrammar
    body: TreeGrammar


@dataclass(frozen=True)
class NaryFuncDecl(Application):
    name: TreeGrammar
    params: TreeGrammar
    return_type: TreeGrammar
    body: TreeGrammar


@dataclass(frozen=True)
class ForLoop(Application):
    init: TreeGrammar
    condition: TreeGrammar
    update: TreeGrammar
    body: TreeGrammar


class WhileLoop(Binary): ...


@dataclass(frozen=True)
class IfThenElse(Application):
    condition: TreeGrammar
    then_branch: TreeGrammar
    else_branch: TreeGrammar


class IfThen(Binary): ...


class CommandSeq(Binary): ...


constructors: list[type[Application]] = [
    Var, BooleanConst, IntConst, NumberTypeLit, BooleanTypeLit, ZaryFuncType, NaryFuncType,
    TypedId, ParamSeq, ArgSeq, Group, ZaryFuncApp, NaryFuncApp, UnaryMinus, IntBinop,
    IntComparison, BooleanBinop, TernaryExpression,
    EmptyBlock, NonemptyBlock, TypedLetDecl, TypedConstDecl, UntypedLetDecl,
    UntypedConstDecl, VarAssignment, VarIncrement, VarPreIncrement, PlusEqualsAssignment,
    ExpressionStatement, ReturnStatement, ZaryFuncDecl, NaryFuncDecl,
    ForLoop, WhileLoop, IfThenElse, IfThen, CommandSeq]

grammar_source = files(__package__).joinpath("typescript.lark").read_text()

exps_lexer_spec, exps_grammar = parse_attribute_grammar(
    constructors, grammar_source, "exp"
).build_parser()
command_seqs_lexer_spec, command_seqs_grammar = parse_attribute_grammar(
    constructors, grammar_source, "command_seq"
).build_parser()
codeblock_lexer_spec, codeblock_grammar = parse_attribute_grammar(
    constructors, grammar_source, "codeblock"
).build_parser()

common_lexer_specs = {
    "exp" : exps_lexer_spec,
    "command_seq" : command_seqs_lexer_spec,
    "codeblock" : codeblock_lexer_spec,
}
common_parsers = {
    "exp" : exps_grammar,
    "command_seq" : command_seqs_grammar,
    "codeblock" : codeblock_grammar,
}

typescript_grammar_checker = RealizabilityChecker(
    lambda asts: asts,
    common_parsers["codeblock"],
    common_lexer_specs["codeblock"],
)
