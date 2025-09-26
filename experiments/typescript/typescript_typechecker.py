from __future__ import annotations
from functools import lru_cache

from core.rewrite import rewrite
from core.grammar import TreeGrammar, EmptySet, Union, as_tree
from core.lexing.token import Token
from llm.realizability import RealizabilityChecker
from .types import *
from .environment import *
from .typescript_abstract_syntax import *


# # # Typepruning functions on TreeGrammars # # #
# A typepruner takes a TreeGrammar, an environment, and a target type,
# and returns a TreeGrammar where some terms of the wrong type
# have been removed.


@rewrite
def typeprune_args(
    env: Environment, exps: TreeGrammar, target_type: Type
) -> TreeGrammar:
    match exps, target_type:
        case Union(children), _:
            return Union.of(
                typeprune_args(env, child, target_type) for child in children
            )
        case ArgSeq(head, tail), TopType():
            return ArgSeq.of(
                typeprune_expression(env, head, TopType()),
                typeprune_args(env, tail, TopType())
            )
        case (ArgSeq(head, tail), ProdType(kids, extensible=extensible)):
            if len(kids) == 0 and not extensible:
                return EmptySet()
            elif len(kids) == 0 and extensible:
                return ArgSeq.of(
                    typeprune_expression(env, head, TopType()),
                    typeprune_args(env, tail, target_type)
                )
            else:
                return ArgSeq.of(
                    typeprune_expression(env, head, kids[0]),
                    typeprune_args(
                        env,
                        tail,
                        ProdType.of(kids[1:], extensible=extensible)
                    )
                )
        case _, TopType():
            return typeprune_expression(env, exps, target_type)
        case _, ProdType(kids, extensible=extensible):
            if len(kids) == 0 and extensible:
                return typeprune_expression(env, exps, target_type)
            elif len(kids) == 1:
                return typeprune_expression(env, exps, kids[0])
            else:
                return EmptySet()
        case _, UnionType(first, second):
            return Union.of(typeprune_args(env, exps, first),
                            typeprune_args(env, exps, second))
    raise ValueError(
        f"Argument sequence got unexpected type {target_type} or term {exps}"
    )


@rewrite
def typeprune_lhs(
    env: Environment, exps: TreeGrammar, target_type: Type, is_mutable: bool
) -> TreeGrammar:
    match exps:
        case Var(tok):
            # TODO: Concretizing the token is a hack, since it may be incomplete.
            # `tok` should be passed directly when the backend supports it.
            tok_tree = as_tree(tok)
            if isinstance(tok_tree, Token):
                return env.get_terms_of_type(
                    tok_tree, target_type, is_mutable=is_mutable
                )
        case Union(children):
            return Union.of(
                typeprune_lhs(env, child, target_type, is_mutable)
                for child in children
            )
    raise ValueError(f"Unexpected lhs in reassignment {exps}")


@rewrite
def typeprune_expression(
    env: Environment, exps: TreeGrammar, target_type: Type
) -> TreeGrammar:
    match exps:
        case IntConst(_):
            return exps if NUMBERTYPE in target_type else EmptySet()
        case BooleanConst():
            return exps if BOOLEANTYPE in target_type else EmptySet()
        case Var(tok):
            # TODO: Concretizing the token is a hack, since it may be incomplete.
            # `tok` should be passed directly when the backend supports it.
            tok_tree = as_tree(tok)
            if isinstance(tok_tree, Token):
                return env.get_terms_of_type(tok_tree, target_type)
            raise ValueError(f"Var has non-token contents: {tok_tree}")
        case ZaryFuncApp(func):
            ftype = FuncType.of(VOIDTYPE, target_type)
            return ZaryFuncApp.of(typeprune_expression(env, func, ftype))
        case NaryFuncApp(func, args):
            func_tree = as_tree(func)
            # If func is incomplete, typecheck func against func[? -> types]
            if func_tree is None:
                target_func_type = FuncType.of(
                    ProdType.of(TopType(), extensible=True), target_type
                )
                return NaryFuncApp.of(
                    typeprune_expression(env, func, target_func_type), args
                )
            # Otherwise, typecheck the args against the real type of func
            else:
                real_func_type = infer_type_expression(env, func_tree)
                if (
                    isinstance(real_func_type, FuncType)
                    and real_func_type.return_type in target_type
                ):
                    return NaryFuncApp.of(
                        func, typeprune_args(env, args, real_func_type.params)
                    )
                return EmptySet()
        # case Group(exps_inner):
        #     good_inners = typeprune_expression(env, exps_inner, target_type)
        #     return Group.of(good_inners)
        case Union(children):
            return Union.of(
                typeprune_expression(env, child, target_type) for child in children
            )
        case EmptySet():
            return EmptySet()
        case Binop(lhs, op, rhs):
            if isinstance(exps, IntBinop) and NUMBERTYPE in target_type:
                good_lhs = typeprune_expression(env, lhs, NUMBERTYPE)
                good_rhs = typeprune_expression(env, rhs, NUMBERTYPE)
                return IntBinop.of(good_lhs, op, good_rhs)
            if isinstance(exps, IntComparison) and BOOLEANTYPE in target_type:
                good_lhs = typeprune_expression(env, lhs, NUMBERTYPE)
                good_rhs = typeprune_expression(env, rhs, NUMBERTYPE)
                return IntComparison.of(good_lhs, op, good_rhs)
            if isinstance(exps, BooleanBinop) and BOOLEANTYPE in target_type:
                good_lhs = typeprune_expression(env, lhs, BOOLEANTYPE)
                good_rhs = typeprune_expression(env, rhs, BOOLEANTYPE)
                return BooleanBinop.of(good_lhs, op, good_rhs)
            return EmptySet()
        case UnaryMinus(val):
            if NUMBERTYPE in target_type:
                good_val = typeprune_expression(env, val, NUMBERTYPE)
                return UnaryMinus.of(good_val)
            return EmptySet()
        case TernaryExpression(guards, then_vals, else_vals):
            return TernaryExpression.of(
                typeprune_expression(env, guards, BOOLEANTYPE),
                typeprune_expression(env, then_vals, target_type),
                typeprune_expression(env, else_vals, target_type)
            )
        case _:
            raise ValueError(f"Unknown expression type: {exps}")


@rewrite
# The type of a statement is its return type.
def typeprune_statement(
    env: Environment, stmts: TreeGrammar, target_type: Type
) -> TreeGrammar:
    match stmts:
        case EmptySet():
            return EmptySet()
        case Union(children):
            return Union.of(
                typeprune_statement(env, child, target_type) for child in children
            )
        case TypedDecl(var_id, type_annotation, rhs):
            if VOIDTYPE not in target_type:
                return EmptySet()
            var_id_tree = as_tree(var_id)
            type_annotation_tree = as_tree(type_annotation)
            # If the var or type declaration is incomplete, there is nothing to do.
            if var_id_tree is None or type_annotation_tree is None:
                return stmts
            # Otherwise, constrain the rhs to the declared type.
            else:
                rhs_type = parse_type(type_annotation_tree)
                return stmts.of(
                    var_id, type_annotation, typeprune_expression(env, rhs, rhs_type)
                )
        case UntypedDecl(var_id, rhs):
            if VOIDTYPE not in target_type:
                return EmptySet()
            var_id_tree = as_tree(var_id)
            # If the var is incomplete, do nothing.
            if var_id_tree is None:
                return stmts
            # Otherwise, make sure the rhs is typesafe.
            else:
                rhs_type = TopType()
                return stmts.of(
                    var_id, typeprune_expression(env, rhs, rhs_type)
                )
        case VarAssignment(var_id, rhs):
            if VOIDTYPE not in target_type:
                return EmptySet()
            var_id_tree = as_tree(var_id)
            # If the var is incomplete, do nothing.
            if var_id_tree is None:
                return VarAssignment.of(
                    typeprune_lhs(env, var_id, TopType(), True), rhs
                )
            # Otherwise, make sure the rhs matches the inferred type of the lhs.
            else:
                var_typ = infer_type_expression(env, var_id_tree)
                if var_typ == EmptyType():
                    return EmptySet()
                else:
                    return VarAssignment.of(
                        typeprune_lhs(env, var_id, TopType(), True),
                        typeprune_expression(env, rhs, var_typ)
                    )
        case PlusEqualsAssignment(var_id, op, rhs):
            if VOIDTYPE not in target_type:
                return EmptySet()
            return PlusEqualsAssignment.of(
                typeprune_lhs(env, var_id, NUMBERTYPE, True),
                op,
                typeprune_expression(env, rhs, NUMBERTYPE),
            )
        case VarIncrement(var_id, op):
            if VOIDTYPE not in target_type:
                return EmptySet()
            return VarIncrement.of(
                typeprune_lhs(env, var_id, NUMBERTYPE, True), op,
            )
        case VarPreIncrement(op, var_id):
            if VOIDTYPE not in target_type:
                return EmptySet()
            return VarPreIncrement.of(
                op, typeprune_lhs(env, var_id, NUMBERTYPE, True),
            )
        case ExpressionStatement(expressions):
            if VOIDTYPE not in target_type:
                return EmptySet()
            return ExpressionStatement.of(
                typeprune_expression(env, expressions, TopType()),
            )
        case ReturnStatement(expressions):
            # TODO: Can ts return void?
            return ReturnStatement.of(
                typeprune_expression(env, expressions, target_type),
            )
        case EmptyBlock():
            return stmts if VOIDTYPE in target_type else EmptySet()
        case NonemptyBlock(commands, ):
            return NonemptyBlock.of(
                typeprune_return_seqs(env, commands, target_type)
            )
        case ZaryFuncDecl(name, return_type, body):
            if VOIDTYPE not in target_type:
                return EmptySet()
            name_tree = as_tree(name)
            return_type_tree = as_tree(return_type)
            # If the name or return type is incomplete, do nothing.
            if name_tree is None or return_type_tree is None:
                return stmts
            # Otherwise, typecheck the body against the declared return type.
            else:
                # Get return output type
                out_type = parse_type(return_type_tree)
                # Binding enables recursion
                func_binding = get_new_bindings(
                    env, ZaryFuncDecl(name_tree, return_type_tree, EmptyBlock())
                )
                new_env = env.add(func_binding)
                return ZaryFuncDecl.of(
                    name, return_type, typeprune_statement(new_env, body, out_type)
                )
        case NaryFuncDecl(name, param_decls, return_type, body):
            if VOIDTYPE not in target_type:
                return EmptySet()
            name_tree = as_tree(name)
            param_decls_tree = as_tree(param_decls)
            return_type_tree = as_tree(return_type)
            # If the name, params, or return type is incomplete, do nothing.
            if (name_tree is None
                or param_decls_tree is None
                    or return_type_tree is None):
                return stmts
            # Otherwise, typecheck the body against the declared return type.
            else:
                # Get return output type
                out_type = parse_type(return_type_tree)
                # Update env by declared paramaters and this function (for recursion)
                func_binding = get_new_bindings(
                    env,
                    NaryFuncDecl(
                        name_tree, param_decls_tree, return_type_tree, EmptyBlock()
                    )
                )
                params_bindings = get_new_bindings(Environment(), param_decls_tree)
                new_env = env.add(func_binding)
                new_env = new_env.add(params_bindings)
                return NaryFuncDecl.of(
                    name, param_decls, return_type,
                    typeprune_statement(new_env, body, out_type)
                )
        case ForLoop(init, condition, update, body):
            # LOOPS IMPLICITLY RETURN VOID BC THEY MAY NOT RUN THE BODY
            if VOIDTYPE not in target_type:
                return EmptySet()
            init_tree = as_tree(init)
            # If the init is incomplete, we can't typecheck the other parts.
            if init_tree is None:
                return ForLoop.of(
                    typeprune_statement(env, init, VOIDTYPE),
                    condition,
                    update,
                    body
                )
            # Otherwise, update the environment and typecheck everything.
            else:
                new_env = env.add(get_new_bindings(env, init_tree))
                return ForLoop.of(
                    typeprune_statement(env, init, VOIDTYPE),
                    typeprune_expression(new_env, condition, BOOLEANTYPE),
                    typeprune_statement(new_env, update, VOIDTYPE),
                    typeprune_statement(new_env, body, target_type)
                )
        case WhileLoop(guard, body):
            if VOIDTYPE not in target_type:
                return EmptySet()
            return WhileLoop.of(
                typeprune_expression(env, guard, BOOLEANTYPE),
                typeprune_statement(env, body, target_type)
            )
        case IfThenElse(guards, then_bodies, else_bodies):
            return IfThenElse.of(
                typeprune_expression(env, guards, BOOLEANTYPE),
                typeprune_statement(env, then_bodies, target_type),
                typeprune_statement(env, else_bodies, target_type)
            )
        case IfThen(guards, then_bodies):
            if VOIDTYPE not in target_type:
                return EmptySet()
            return IfThen.of(
                typeprune_expression(env, guards, BOOLEANTYPE),
                typeprune_statement(env, then_bodies, target_type)
            )
    return EmptySet()


@rewrite
def typeprune_return_seqs(
    env: Environment, stmts: TreeGrammar, target_type: Type
) -> TreeGrammar:
    match stmts:
        case Union(children):
            return Union.of(
                typeprune_return_seqs(env, child, target_type)
                for child in children
            )
        case CommandSeq(head, tail):
            head_tree = as_tree(head)
            # If head is incomplete, head can return or be void,
            # and we don't typecheck tail.
            if head_tree is None:
                possibly_void_target_type = target_type
                if VOIDTYPE not in target_type:
                    possibly_void_target_type = UnionType.of(target_type, VOIDTYPE)
                return CommandSeq.of(
                    typeprune_statement(env, head, possibly_void_target_type),
                    tail
                )
            # Otherwise, we can typecheck tail.
            else:
                # TODO: Infer the type of head here instead of this hack.
                # Update the environment if head is complete.
                after_head_env = env.add(get_new_bindings(env, head_tree))
                # Either head matches a concrete [non void] type and tail is any,
                # or head is void and tail matches the target type
                non_void_target_type = get_non_void(target_type)
                possibly_void_target_type = target_type
                if VOIDTYPE not in target_type:
                    possibly_void_target_type = UnionType.of(target_type, VOIDTYPE)
                return Union.of(
                    CommandSeq.of(
                        typeprune_statement(env, head, non_void_target_type),
                        typeprune_return_seqs(after_head_env, tail, TopType()),
                    ),
                    CommandSeq.of(
                        typeprune_statement(env, head, possibly_void_target_type),
                        typeprune_return_seqs(after_head_env, tail, target_type),
                    )
                )
        case _:
            return typeprune_statement(env, stmts, target_type)


# # # Type inference functions on Concrete ASTs # # #


@lru_cache()
def parse_type(type_expression: TreeGrammar) -> Type:
    """"WARNING: ONLY INVOKE THIS FUNCTION ON COMPLETELY PARSED TREEGRAMMARS"""
    match type_expression:
        case NumberTypeLit():
            return NUMBERTYPE
        case BooleanTypeLit():
            return BOOLEANTYPE
        case ZaryFuncType(return_type,):
            return FuncType.of(VOIDTYPE, parse_type(return_type))
        case NaryFuncType(typed_params, return_type):
            param_types = (
                binding[1] for binding in get_new_bindings(Environment(), typed_params)
            )
            return FuncType.of(ProdType.of(param_types), parse_type(return_type))
        case _:
            return EmptyType()


@lru_cache()
def infer_type_expression(env: Environment, exp: TreeGrammar) -> Type:
    match exp:
        case IntConst(_):
            return NUMBERTYPE
        case BooleanConst():
            return BOOLEANTYPE
        case Var(var) if isinstance(var, Token):
            return env._get_typed(var.prefix, TopType())[1]
        case ZaryFuncApp(func,):
            functype = infer_type_expression(env, func)
            if isinstance(functype, FuncType):
                return functype.return_type
            else:
                return EmptyType()
        case NaryFuncApp(func, args):
            functype = infer_type_expression(env, func)
            args_type = infer_type_args(env, args)
            if isinstance(functype, FuncType) and args_type in functype.params:
                return functype.return_type
            return EmptyType()
        case Binop(_, _, _):
            return NUMBERTYPE if exp is IntBinop else BOOLEANTYPE
        case UnaryMinus(_):
            return NUMBERTYPE
        case TernaryExpression(_, then_val, else_val):
            then_type = infer_type_expression(env, then_val)
            else_type = infer_type_expression(env, else_val)
            return (then_type if then_type == else_type else EmptyType())
        case Union(children):
            types = {
                infer_type_expression(env, child) for child in children
            }.difference({EmptyType()})
            if len(types) == 0:
                return EmptyType()
            elif len(types) == 1:
                return types.pop()
            raise ValueError(
                f"Unexpected type(s) {types} for concrete expression {exp}"
            )
        case _:
            raise ValueError(f"Unexpected concrete expression {exp}")


@lru_cache()
def infer_type_args(env: Environment, args: TreeGrammar) -> Type:
    match args:
        case EmptySet():
            return EmptyType()
        case Union(children):
            updates = {
                infer_type_args(env, child) for child in children
            }.difference({EmptyType()})
            if len(updates) == 0:
                return EmptyType()
            elif len(updates) == 1:
                return updates.pop()
            raise ValueError(f"infer_type_args called on ambiguous args {args}")
        case ArgSeq(head, tail):
            tail_type = infer_type_args(env, tail)
            if isinstance(tail_type, ProdType):
                return ProdType.of(
                    infer_type_expression(env, head), *(tail_type.types)
                )
            return EmptyType()
        case _:
            return ProdType.of(infer_type_expression(env, args))


@lru_cache()
def get_new_bindings(env: Environment, stmt: TreeGrammar
                     ) -> tuple[tuple[str, Type, bool], ...]:
    """WARNING: DO NOT CALL ON INCOMPLETE TREEGRAMMAR."""
    match stmt:
        case EmptySet():
            return tuple()
        case Union(children):
            updates = {
                get_new_bindings(env, child) for child in children
            }.difference({tuple()})
            if len(updates) == 0:
                return tuple()
            elif len(updates) == 1:
                return updates.pop()
            raise ValueError(f"gather_env_update called on ambiguous stmt {stmt}")
        case TypedLetDecl(var, type, _):
            var_tree = as_tree(var)
            return ((get_identifier_name(var_tree), parse_type(type), True),)
        case TypedConstDecl(var, type, _):
            var_tree = as_tree(var)
            return ((get_identifier_name(var_tree), parse_type(type), False),)
        case UntypedLetDecl(var, rhs):
            var_tree = as_tree(var)
            return ((
                get_identifier_name(var_tree), infer_type_expression(env, rhs), True
            ),)
        case UntypedConstDecl(var, rhs):
            var_tree = as_tree(var)
            return ((
                get_identifier_name(var_tree), infer_type_expression(env, rhs), False
            ),)
        case ZaryFuncDecl(func, return_type, _):
            func_tree = as_tree(func)
            return ((
                get_identifier_name(func_tree),
                FuncType.of(VOIDTYPE, parse_type(return_type)),
                False
            ),)
        case NaryFuncDecl(func, params, return_type, _):
            func_tree = as_tree(func)
            params_tree = as_tree(params)
            return ((
                get_identifier_name(func_tree),
                FuncType.of(type_of_params(params_tree),
                            parse_type(return_type)),
                False
            ),)
        case ParamSeq(head, tail):
            return get_new_bindings(env, head) + get_new_bindings(env, tail)
        case TypedId(var, type_signature):
            var_tree = as_tree(var)
            return ((get_identifier_name(var_tree), parse_type(type_signature), True),)
        case _:
            return tuple()


@lru_cache(maxsize=None)
def get_identifier_name(exp: TreeGrammar | None) -> str:
    """WARNING: DO NOT CALL ON INCOMPLETE TREEGRAMMAR."""
    match exp:
        case Var(var) if isinstance(var, Token):
            return var.prefix
    return ""


@lru_cache(maxsize=None)
def type_of_params(params: TreeGrammar | None) -> ProdType | EmptyType:
    """WARNING: DO NOT CALL ON INCOMPLETE TREEGRAMMAR."""
    match params:
        case EmptySet():
            return EmptyType()
        case Union(children):
            updates = {
                type_of_params(child) for child in children
            }.difference({EmptyType()})
            if len(updates) == 0:
                return EmptyType()
            elif len(updates) == 1:
                return updates.pop()
            raise ValueError(f"type_of_params called on ambiguous params {params}")
        case ParamSeq(head, tail):
            head_types = type_of_params(head)
            tail_types = type_of_params(tail)
            if (
                isinstance(head_types, ProdType)
                and isinstance(tail_types, ProdType)
            ):
                return ProdType.of(
                    *(head_types.types), *(tail_types.types)
                )
            return EmptyType()
        case TypedId(_, type_annotation):
            return ProdType.of(parse_type(type_annotation))
        case _:
            raise ValueError(f"Unexpected param type {params}")


default_env = Environment.from_dict({
    "Math.PI": NUMBERTYPE,
    "Math.pow": FuncType.of(ProdType.of(NUMBERTYPE, NUMBERTYPE), NUMBERTYPE),
    "Math.log2": FuncType.of(ProdType.of(NUMBERTYPE), NUMBERTYPE),
    "Math.sqrt": FuncType.of(ProdType.of(NUMBERTYPE), NUMBERTYPE),
    "Math.floor": FuncType.of(ProdType.of(NUMBERTYPE), NUMBERTYPE),
    "Math.round": FuncType.of(ProdType.of(NUMBERTYPE), NUMBERTYPE),
    "Math.ceil": FuncType.of(ProdType.of(NUMBERTYPE), NUMBERTYPE),
    "Math.clz32": FuncType.of(ProdType.of(NUMBERTYPE), NUMBERTYPE),
    # Min and max types are slightly imprecise, but whatever
    "Math.min": FuncType.of(ProdType.of(NUMBERTYPE, extensible=True), NUMBERTYPE),
    "Math.max": FuncType.of(ProdType.of(NUMBERTYPE, extensible=True), NUMBERTYPE),
})

typescript_typechecker = RealizabilityChecker(
    lambda asts: typeprune_return_seqs(default_env, asts, VOIDTYPE),
    common_parsers["codeblock"],
    common_lexer_specs["codeblock"],
)
