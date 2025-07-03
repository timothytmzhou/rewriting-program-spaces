from __future__ import annotations

from core.parser import *
from core.grammar import *
from lexing.leaves import Token
from runllm.constrained_decoding import RealizabilityChecker
from .types import *
from .environment import *
from .typescript_grammar import *


@rewrite
def typecheck_args(env: Environment, exps: TreeGrammar, types: Type
                   ) -> TreeGrammar:
    match exps, types:
        case Union(children), _:
            return Union.of(typecheck_args(env, child, types) for child in children)
        case Application("arg sequence", (head, tail)), TopType():
            return Application.of("arg_sequence",
                                  typecheck_expression(env, head, TopType()),
                                  typecheck_args(env, tail, TopType())
                                  )
        case (Application("arg sequence", (head, tail)),
              ProdType(kids, extensible=extensible)):
            if len(kids) == 0:
                if extensible:
                    return Application.of("arg_sequence",
                                          typecheck_expression(env, head, TopType()),
                                          typecheck_args(env, tail, types)
                                          )
                return EmptySet()
            return Application.of("arg_sequence",
                                  typecheck_expression(env, head, kids[0]),
                                  typecheck_args(
                                      env,
                                      tail,
                                      ProdType.of(kids[1:],
                                                  extensible=extensible)
                                  )
                                  )
        case _, TopType():
            return typecheck_expression(env, exps, types)
        case _, ProdType(kids, extensible=extensible):
            if len(kids) == 0 and extensible:
                return typecheck_expression(env, exps, types)
            elif len(kids) == 1:
                return typecheck_expression(env, exps, kids[0])
            else:
                return EmptySet()
    raise ValueError(f"Argument sequence got unexpected type {types} or term {exps}")


@rewrite
def typecheck_expression(env: Environment, exps: TreeGrammar, types: Type
                         ) -> TreeGrammar:
    match exps:
        case Constant(c) if isinstance(c, Token) and c.token_type == "int":
            if NUMBERTYPE in types:
                return exps
            else:
                return EmptySet()
        case Constant(c) if isinstance(c, Token) and c.token_type == "str":
            if STRINGTYPE in types:
                return exps
            else:
                return EmptySet()
        case Constant(c) if (isinstance(c, Token)
                             and (c.token_type in {"true", "false"})):
            if BOOLEANTYPE in types:
                return exps
            else:
                return EmptySet()
        case Constant(c) if isinstance(c, Token) and c.token_type == "id":
            return env.get_terms_of_type(c, types)
        case Application("0-ary lambda", (bodies,), focus=focus):
            match types:
                case TopType():
                    return Application.of("0-ary lambda",
                                          (typecheck_return(env, bodies, types),),
                                          focus=focus)
                case FuncType(ProdType.of(), return_type):
                    return Application.of("0-ary lambda",
                                          (typecheck_return(env, bodies, return_type),),
                                          focus=focus)
            return EmptySet()
        case Application("0-ary app", (func,), focus=focus):
            ftype = FuncType.of(ProdType.of(), types)
            return Application.of("0-ary app",
                                  typecheck_expression(env, func, ftype), focus=focus)
        case Application("n-ary app", (func, args), focus=focus):
            # If func is incomplete, just typecheck it against func[? -> types]
            if focus == 0:
                function_type = FuncType.of(
                    ProdType.of(TopType(), extensible=True),
                    types)
                return Application.of("n-ary app",
                                      (typecheck_expression(env, func, function_type),
                                       args),
                                      focus=focus)
            func_type = infer_type_expression(env, func)
            if isinstance(func_type, FuncType):
                return (Application.of("n-ary app",
                                       (func,
                                        typecheck_args(env, args, func_type.params)),
                                       focus=focus)
                        if func_type.return_type in types
                        else EmptySet())
            return EmptySet()
        case Application("grp", (exps_inner,), focus=focus):
            good_inners = typecheck_expression(env, exps_inner, types)
            return Application.of("grp", good_inners, focus=focus)
        case Union(children):
            return Union.of(typecheck_expression(env, child, types)
                            for child in children)
        case EmptySet():
            return EmptySet()
        case Application(op, (lhs, rhs), focus=focus) if (
                op in {"+", "-", "*", "/", "%", "<", "<=", ">", ">=", "==", "!=="}):
            if op in {"+", "-", "*", "/", "%"} and NUMBERTYPE in types:
                good_lhs = typecheck_expression(env, lhs, NUMBERTYPE)
                good_rhs = typecheck_expression(env, rhs, NUMBERTYPE)
                return Application.of(op, (good_lhs, good_rhs), focus=focus)
            if op in {"<", "<=", ">", ">=", "==", "!=="} and BOOLEANTYPE in types:
                good_lhs = typecheck_expression(env, lhs, NUMBERTYPE)
                good_rhs = typecheck_expression(env, rhs, NUMBERTYPE)
                return Application.of(op, (good_lhs, good_rhs), focus=focus)
            return EmptySet()
        case _:
            raise ValueError(f"Unknown expression type: {exps}")


@rewrite
def typecheck_return(env: Environment, stmts: TreeGrammar, typ: Type) -> TreeGrammar:
    match stmts:
        case EmptySet():
            return EmptySet()
        case Union(children):
            return Union.of(typecheck_return(env, child, typ) for child in children)
        case Application("variable declaration",
                         (var_id, type_annotation, rhs), focus=focus):
            if ProdType.of() not in typ:
                return EmptySet()
            if focus < 2:
                return stmts
            else:
                rhs_type = parse_type(type_annotation)
                return (Application.of("variable declaration",
                                       (var_id, type_annotation,
                                        typecheck_expression(env, rhs, rhs_type)),
                                       focus=focus)
                        if ProdType.of() in typ
                        else EmptySet())
        case Application("expression statement", (expressions, ), focus=focus):
            return (Application.of("expression statement",
                                   typecheck_expression(env, expressions, TopType()),
                                   focus=focus)
                    if ProdType.of() in typ
                    else EmptySet())
        case Application("return statement", (expressions, ), focus=focus):
            return Application.of("return statement",
                                  typecheck_expression(env, expressions, typ),
                                  focus=focus)
        case Application("empty block"):
            return stmts if ProdType.of() in typ else EmptySet()
        case Application("nonempty block", (commands, ), focus=focus):
            return Application.of("nonempty block",
                                  typecheck_return_seqs(env, commands, typ),
                                  focus=focus)
        case Application("0-ary func decl",
                         (func_id, return_types, bodies), focus=focus):
            if focus < 2:
                return (stmts
                        if ProdType.of() in typ
                        else EmptySet())
            else:
                return_type = parse_type(return_types)
                return (Application.of("0-ary func decl",
                                       (func_id,
                                        return_types,
                                        typecheck_return(env, bodies, return_type)))
                        if ProdType.of() in typ
                        else EmptySet())
        case Application("n-ary func decl",
                         (func_id, param_decls, return_types, bodies), focus=focus):
            if focus < 3:
                return (stmts
                        if VOIDTYPE in typ
                        else EmptySet())
            else:
                # Get return type
                return_type = parse_type(return_types)
                # Update env by declared paramaters
                updated_env = env.add(get_new_bindings(param_decls))
                return (Application.of("n-ary func decl",
                                       (func_id,
                                        param_decls,
                                        return_types,
                                        typecheck_return(updated_env, bodies,
                                                         return_type)))
                        if VOIDTYPE in typ
                        else EmptySet())
        # case Application("if-then-else", (guards, then_bodies, else_bodies)):
        #     legal_guards = typecheck_expression(env, guards, BOOLEANTYPE)
        #     legal_then_bodies = typecheck_return(env, then_bodies, typ)
        #     if focus < 2:
        #         return_type = typ
        #     else:
        #         # TODO: Implement type inference for return types
        #         return_type = typ
        #         # return_type = infer_return_type(legal_then_bodies)
        #     legal_else_bodies = typecheck_return(env, else_bodies, return_type)
        #     return Application.of("if-then-else",
        #                             legal_guards,
        #                             legal_then_bodies,
        #                             legal_else_bodies,
        #                             focus=focus)
    return EmptySet()


@rewrite
def typecheck_return_seqs(env: Environment, stmts: TreeGrammar, typ: Type
                          ) -> TreeGrammar:
    match stmts:
        case Union(children):
            return Union.of(typecheck_return_seqs(env, child, typ)
                            for child in children)
        case Application("command seq", (head, tail), focus=focus):
            updated_env = (env.add(get_new_bindings(head)) if focus > 0 else env)
            # Either head matches an acceptable [non void] type and tail is any,
            # or head is void and tail matches the target type
            non_void_typ = get_non_void(typ)
            return Union.of(
                Application.of("command seq",
                               (typecheck_return(env, head, non_void_typ),
                                typecheck_return_seqs(updated_env, tail, TopType())),
                               focus=focus),
                Application.of("command seq",
                               (typecheck_return(env, head, VOIDTYPE),
                                typecheck_return_seqs(updated_env, tail, typ)),
                               focus=focus)
            )
        case _:
            return typecheck_return(env, stmts, typ)


@fixpoint(lambda: EmptyType())
def parse_type(type_expression: TreeGrammar) -> Type:
    """"WARNING: ONLY INVOKE THIS FUNCTION ON COMPLETELY PARSED TREEGRAMMARS"""
    match type_expression:
        case Constant(c) if isinstance(c, Token) and c.token_type == "numbertype":
            return NUMBERTYPE
        case Constant(c) if isinstance(c, Token) and c.token_type == "stringtype":
            return STRINGTYPE
        case Constant(c) if (isinstance(c, Token) and (c.token_type == "booltype")):
            return BOOLEANTYPE
        case Application("0-ary functype", (return_type,)):
            return FuncType.of(ProdType.of(), parse_type(return_type))
        case Application("n-ary functype", (arg_types, return_type)):
            return FuncType.of(parse_type_seq(arg_types),
                               parse_type(return_type))
    raise ValueError(f"Unexpected type expression {type_expression}")


@fixpoint(lambda: ProdType.of())
def parse_type_seq(product_type_expression: TreeGrammar) -> ProdType | EmptyType:
    """"WARNING: ONLY INVOKE THIS FUNCTION ON COMPLETELY PARSED TREEGRAMMARS"""
    match product_type_expression:
        case Application("type sequence", (head, tail)):
            return ProdType.of(parse_type(head), *(parse_type_seq(tail).types))
        case _:
            return ProdType.of(parse_type(product_type_expression))


# TODO: Modify fixpoint so I can pass additional args.
infer_type_expression_helper_functions: dict[Environment, Callable] = dict()


def infer_type_expression(env: Environment, exp: TreeGrammar) -> Type:
    @fixpoint(lambda: ProdType.of())
    def infer_type_expression_fixedenv(exp: TreeGrammar) -> Type:
        match exp:
            case Constant(c) if isinstance(c, Token) and c.token_type == "int":
                return NUMBERTYPE
            case Constant(c) if isinstance(c, Token) and c.token_type == "str":
                return STRINGTYPE
            case Constant(c) if (isinstance(c, Token)
                                 and (c.token_type in {"true", "false"})):
                return BOOLEANTYPE
            case Constant(c) if isinstance(c, Token) and c.token_type == "id":
                return env._get_typed(c.prefix, TopType())[1]
            case Application("0-ary app", (func,)):
                functype = infer_type_expression_fixedenv(func)
                if isinstance(functype, FuncType):
                    return functype.return_type
                elif isinstance(functype, EmptyType):
                    return EmptyType()
                raise ValueError(f"Unexpected type {functype} for function {func}")
            case Application("n-ary app", (func, args)):
                functype = infer_type_expression_fixedenv(func)
                args_type = infer_type_args(env, args)
                if isinstance(functype, FuncType) and args_type in functype.params:
                    return functype.return_type
                return EmptyType()
            case Application("grp", (exp_inner,)):
                return infer_type_expression_fixedenv(exp_inner)
            case Application(op, (_, _)) if (
                    op in {"+", "-", "*", "/", "%", "<", "<=", ">", ">=", "==", "!=="}):
                if op in {"+", "-", "*", "/", "%"}:
                    return NUMBERTYPE
                if op in {"<", "<=", ">", ">=", "==", "!=="}:
                    return BOOLEANTYPE
            case Union(children):
                types = {infer_type_expression_fixedenv(child) for child in children
                         }.difference({EmptyType()})
                if len(types) != 1:
                    raise ValueError(f"Unexpected type(s) {types} for expression {exp}")
                return types.pop()
            case _:
                # TODO: Fixpoint shouldn't evaluate the function on unneeded children.
                # I'd prefer to throw an error in this case, but I can't.
                return EmptyType()
    if env not in infer_type_expression_helper_functions:
        infer_type_expression_helper_functions[env] = infer_type_expression_fixedenv
    return infer_type_expression_helper_functions[env](exp)


infer_type_agrs_helper_functions: dict[Environment, Callable] = dict()


def infer_type_args(env: Environment, args: TreeGrammar) -> Type:
    @fixpoint(lambda: ProdType.of())
    def infer_type_args_helper(args: TreeGrammar) -> Type:
        match args:
            case EmptySet():
                return EmptyType()
            case Union(children):
                updates = {infer_type_args_helper(child) for child in children
                           }.difference({EmptyType()})
                if len(updates) == 1:
                    return updates.pop()
                if len(updates) > 1:
                    raise ValueError(f"infer_type_args called on ambiguous args {args}")
                return EmptyType()
            case Application("arg sequence", (head, tail)):
                return ProdType.of(infer_type_expression(env, head),
                                   *(infer_type_args_helper(tail).types))
            case _:
                return ProdType.of(infer_type_expression(env, args))
    if env not in infer_type_agrs_helper_functions:
        infer_type_agrs_helper_functions[env] = infer_type_args_helper
    return infer_type_agrs_helper_functions[env](args)


@fixpoint(lambda: tuple())
def get_new_bindings(stmt: TreeGrammar) -> tuple[tuple[str, Type], ...]:
    """WARNING: DO NOT CALL ON INCOMPLETE TREEGRAMMAR."""
    match stmt:
        case EmptySet():
            return tuple()
        case Union(children):
            updates = {get_new_bindings(child) for child in children}.difference(
                {tuple()})
            if len(updates) == 1:
                return updates.pop()
            if len(updates) > 1:
                raise ValueError(f"gather_env_update called on ambiguous stmt {stmt}")
            return tuple()
        case Application("variable declaration", (var, type, _)):
            return ((get_identifier_name(var), parse_type(type)), )
        case Application("0-ary func decl", (func, return_type, _)):
            return ((get_identifier_name(func), FuncType.of(ProdType.of(),
                                                            parse_type(return_type))), )
        case Application("n-ary func decl", (func, params, return_type, _)):
            return ((get_identifier_name(func), FuncType.of(type_of_params(params),
                                                            parse_type(return_type))), )
        case Application("param sequence", (head, tail)):
            return get_new_bindings(head) + get_new_bindings(tail)
        case Application("typed_id", (var, type_signature)):
            return ((get_identifier_name(var), parse_type(type_signature)),)
        case _:
            return tuple()


@fixpoint(lambda: "")
def get_identifier_name(exp: TreeGrammar) -> str:
    """WARNING: DO NOT CALL ON INCOMPLETE TREEGRAMMAR."""
    match exp:
        case Constant(c) if isinstance(c, Token) and c.token_type == "id":
            return c.prefix
    raise ValueError(f"Unexpected identifier {exp}")


@fixpoint(lambda: ProdType.of())
def type_of_params(params: TreeGrammar) -> ProdType | EmptyType:
    """WARNING: DO NOT CALL ON INCOMPLETE TREEGRAMMAR."""
    match params:
        case EmptySet():
            return EmptyType()
        case Union(children):
            updates = {type_of_params(child) for child in children}.difference(
                {EmptyType()})
            if len(updates) == 1:
                return updates.pop()
            if len(updates) > 1:
                raise ValueError(f"infer_type_args called on ambiguous args {args}")
            return EmptyType()
        case Application("param sequence", (head, tail)):
            return ProdType.of(*(type_of_params(head).types),
                               *(type_of_params(tail).types))
        case Application("typed_id", (_, type_annotation)):
            return ProdType.of(parse_type(type_annotation))
        case _:
            # TODO: Fixpoint shouldn't evaluate the function on unneeded children.
            # I'd prefer to throw an error in this case, but I can't.
            return EmptyType()


typescript_checker = RealizabilityChecker(
    lambda asts: typecheck_return_seqs(Environment(), asts, VOIDTYPE),
    commands(),
    lexer_spec,
)
