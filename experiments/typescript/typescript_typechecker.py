from __future__ import annotations

from core.parser import *
from core.grammar import *
from lexing.token import Token
from llm.realizability import RealizabilityChecker
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
        case _, UnionType(first, second):
            return Union.of(typecheck_args(env, exps, first),
                            typecheck_args(env, exps, second))
    raise ValueError(f"Argument sequence got unexpected type {types} or term {exps}")


# @rewrite
# def typecheck_dot_access(env: Environment, exps: TreeGrammar, types: Type,
#                          lhs_type: Type) -> TreeGrammar:
#     match exps:
#         case Union(children):
#             return Union.of(typecheck_dot_access(env, child, types, lhs_type)
#                             for child in children)
#         case Constant(c) if isinstance(c, Token) and c.token_type == "id":
#             return env.get_terms_of_type(c, types, lhs_type=lhs_type)
#         case _:
#             raise ValueError(f"Unknown dot access rhs: {exps}")


@rewrite
def typecheck_lhs(env: Environment, exps: TreeGrammar, types: Type,
                  is_mutable: bool) -> TreeGrammar:
    match exps:
        case Token(token_type="id") as t:
            return env.get_terms_of_type(t, types, is_mutable=is_mutable)
    raise ValueError(f"Unexpected lhs in reassignment {exps}")


@rewrite
def typecheck_expression(env: Environment, exps: TreeGrammar, types: Type
                         ) -> TreeGrammar:
    match exps:
        case Token(token_type="int"):
            if NUMBERTYPE in types:
                return exps
            else:
                return EmptySet()
        case Token(token_type="str"):
            if STRINGTYPE in types:
                return exps
            else:
                return EmptySet()
        case Token(token_type="true"):
            if BOOLEANTYPE in types:
                return exps
            else:
                return EmptySet()
        case Token(token_type="false"):
            if BOOLEANTYPE in types:
                return exps
            else:
                return EmptySet()
        case Token(token_type="id") as t:
            return env.get_terms_of_type(t, types)
        # case Application("0-ary lambda", (bodies,), focus=focus):
        #     match types:
        #         case UnionType(first, second):
        #             return Union.of(typecheck_expression(env, exps, first),
        #                             typecheck_expression(env, exps, second))
        #         case TopType():
        #             return Application.of("0-ary lambda",
        #                                   (typecheck_return(env, bodies, types),),
        #                                   focus=focus)
        #         case FuncType(VOIDTYPE, return_type):
        #             return Application.of("0-ary lambda",
        #                                   (typecheck_return(env, bodies,
        #                                                     return_type),),
        #                                   focus=focus)
        #     return EmptySet()
        case Application("0-ary app", (func,), focus=focus):
            ftype = FuncType.of(VOIDTYPE, types)
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
        # case Application("dot access", (lhs, rhs), focus=focus):
        #     if focus < 1:
        #         return Application("dot access", (lhs, rhs), focus=focus)
        #     lhs_type = infer_type_expression(env, lhs)
        #     return Union.of(
        #         (Application("dot access",
        #                      (lhs, typecheck_dot_access(env, rhs, types, NUMBERTYPE)),
        #                      focus=focus)
        #          if NUMBERTYPE in lhs_type
        #          else EmptySet()),
        #         (Application("dot access",
        #                      (lhs, typecheck_dot_access(env, rhs, types, STRINGTYPE)),
        #                      focus=focus)
        #          if STRINGTYPE in lhs_type
        #          else EmptySet())
        #     )
        case Union(children):
            return Union.of(typecheck_expression(env, child, types)
                            for child in children)
        case EmptySet():
            return EmptySet()
        case Application(op, (lhs, rhs), focus=focus) if op in BINOP:
            if op in BINOP_INT_INT_TO_INT and NUMBERTYPE in types:
                good_lhs = typecheck_expression(env, lhs, NUMBERTYPE)
                good_rhs = typecheck_expression(env, rhs, NUMBERTYPE)
                return Application.of(op, (good_lhs, good_rhs), focus=focus)
            if op in BINOP_INT_INT_TO_BOOL and BOOLEANTYPE in types:
                good_lhs = typecheck_expression(env, lhs, NUMBERTYPE)
                good_rhs = typecheck_expression(env, rhs, NUMBERTYPE)
                return Application.of(op, (good_lhs, good_rhs), focus=focus)
            if op in BINOP_BOOL_BOOL_TO_BOOL and BOOLEANTYPE in types:
                good_lhs = typecheck_expression(env, lhs, BOOLEANTYPE)
                good_rhs = typecheck_expression(env, rhs, BOOLEANTYPE)
                return Application.of(op, (good_lhs, good_rhs), focus=focus)
            return EmptySet()
        case Application("ternary expression", (then_vals, guards, else_vals),
                         focus=focus):
            if focus < 1:
                return Application.of("ternary expression",
                                      (typecheck_expression(env, then_vals, types),
                                       typecheck_expression(env, guards, BOOLEANTYPE),
                                       typecheck_expression(env, else_vals, types)),
                                      focus=focus)
            exp_type = infer_type_expression(env, then_vals)
            return (Application.of("ternary expression",
                                   (typecheck_expression(env, then_vals, types),
                                    typecheck_expression(env, guards, BOOLEANTYPE),
                                    typecheck_expression(env, else_vals, types)),
                                   focus=focus)
                    if exp_type in types
                    else EmptySet())
        case _:
            raise ValueError(f"Unknown expression type: {exps}")


@rewrite
def typecheck_return(env: Environment, stmts: TreeGrammar, typ: Type) -> TreeGrammar:
    match stmts:
        case EmptySet():
            return EmptySet()
        case Union(children):
            return Union.of(typecheck_return(env, child, typ) for child in children)
        case Application(decl, (var_id, type_annotation, rhs),
                         focus=focus) if decl in {"variable declaration",
                                                  "const declaration"}:
            if VOIDTYPE not in typ:
                return EmptySet()
            if focus < 2:
                return stmts
            else:
                rhs_type = parse_type(type_annotation)
                return (Application.of(decl,
                                       (var_id, type_annotation,
                                        typecheck_expression(env, rhs, rhs_type)),
                                       focus=focus)
                        if VOIDTYPE in typ
                        else EmptySet())
        case Application("variable assignment",
                         (var_id, rhs), focus=focus):
            if VOIDTYPE not in typ:
                return EmptySet()
            if focus < 1:
                return Application.of("variable assignment",
                                      (typecheck_lhs(env, var_id, TopType(), True),
                                       rhs),
                                      focus=focus)
            else:
                var_typ = infer_type_expression(env, var_id)
                return (Application.of("variable assignment",
                                       (typecheck_lhs(env, var_id, var_typ, True),
                                        typecheck_expression(env, rhs, var_typ)),
                                       focus=focus)
                        if VOIDTYPE in typ and not isinstance(var_typ, EmptyType)
                        else EmptySet())
        case Application("+= assignment", (var_id, rhs), focus=focus):
            if VOIDTYPE not in typ:
                return EmptySet()
            if focus < 1:
                return Application.of("+= assignment",
                                      (typecheck_lhs(env, var_id, NUMBERTYPE, True),
                                       rhs),
                                      focus=focus)
            else:
                var_typ = infer_type_expression(env, var_id)
                return (Application.of("+= assignment",
                                       (typecheck_lhs(env, var_id, var_typ, True),
                                        typecheck_expression(env, rhs, NUMBERTYPE)),
                                       focus=focus)
                        if VOIDTYPE in typ and NUMBERTYPE in var_typ
                        else EmptySet())
        case Application("increment", (var_id, ), focus=focus):
            if VOIDTYPE not in typ:
                return EmptySet()
            return Application.of("increment",
                                  (typecheck_lhs(env, var_id, NUMBERTYPE, True), ),
                                  focus=focus)
        case Application("expression statement", (expressions, ), focus=focus):
            return (Application.of("expression statement",
                                   typecheck_expression(env, expressions, TopType()),
                                   focus=focus)
                    if VOIDTYPE in typ
                    else EmptySet())
        case Application("return statement", (expressions, ), focus=focus):
            # TODO: Can ts return void?
            return Application.of("return statement",
                                  typecheck_expression(env, expressions, typ),
                                  focus=focus)
        case Application("empty block"):
            return stmts if VOIDTYPE in typ else EmptySet()
        case Application("nonempty block", (commands, ), focus=focus):
            return Application.of("nonempty block",
                                  typecheck_return_seqs(env, commands, typ),
                                  focus=focus)
        case Application("0-ary func decl",
                         (func_id, return_types, bodies), focus=focus):
            if focus < 2:
                return (stmts
                        if VOIDTYPE in typ
                        else EmptySet())
            else:
                return_type = parse_type(return_types)
                new_env = env.add(get_new_bindings(stmts))  # Binding enables recursion
                return (Application.of("0-ary func decl",
                                       (func_id,
                                        return_types,
                                        typecheck_return(new_env, bodies, return_type)))
                        if VOIDTYPE in typ
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
                # Update env by declared paramaters and this function (for recursion)
                new_env = env.add(get_new_bindings(stmts))
                new_env = new_env.add(get_new_bindings(param_decls))
                return (Application.of("n-ary func decl",
                                       (func_id,
                                        param_decls,
                                        return_types,
                                        typecheck_return(new_env, bodies,
                                                         return_type)))
                        if VOIDTYPE in typ
                        else EmptySet())
        case Application("for loop", (init, condition, update, body), focus=focus):
            # LOOPS IMPLICITLY RETURN VOID BC THEY MAY NOT RUN THE BODY
            if VOIDTYPE not in typ:
                return EmptySet()
            if focus < 1:
                return Application.of("for loop",
                                      (typecheck_return(env, init, VOIDTYPE),
                                       condition,
                                       update,
                                       body),
                                      focus=focus)
            else:
                new_env = env.add(get_new_bindings(init))
                return Application.of("for loop",
                                      (typecheck_return(env, init, VOIDTYPE),
                                       typecheck_expression(new_env, condition,
                                                            BOOLEANTYPE),
                                       typecheck_return(new_env, update, VOIDTYPE),
                                       typecheck_return(new_env, body, typ)),
                                      focus=focus)
        case Application("while loop", (guard, body), focus=focus):
            if VOIDTYPE not in typ:
                return EmptySet()
            return Application.of("while loop",
                                  (typecheck_expression(env, guard, BOOLEANTYPE),
                                   typecheck_return(env, body, typ)),
                                  focus=focus)
        case Application("if-then-else",
                         (guards, then_bodies, else_bodies),
                         focus=focus):
            legal_guards = typecheck_expression(env, guards, BOOLEANTYPE)
            legal_then_bodies = typecheck_return(env, then_bodies, typ)
            legal_else_bodies = typecheck_return(env, else_bodies, typ)
            return Application.of("if-then-else",
                                  (legal_guards,
                                   legal_then_bodies,
                                   legal_else_bodies),
                                  focus=focus)
        case Application("if-then",
                         (guards, then_bodies),
                         focus=focus):
            return (Application.of("if-then",
                                   (typecheck_expression(env, guards, BOOLEANTYPE),
                                    typecheck_return(env, then_bodies, typ)),
                                   focus=focus)
                    if VOIDTYPE in typ
                    else EmptySet())
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
            # Either head matches a concrete [non void] type and tail is any,
            # or head is void and tail matches the target type
            non_void_typ = get_non_void(typ)
            possibly_void_type = typ if VOIDTYPE in typ else UnionType.of(typ, VOIDTYPE)
            return Union.of(
                Application.of("command seq",
                               (typecheck_return(env, head, non_void_typ),
                                typecheck_return_seqs(updated_env, tail, TopType())),
                               focus=focus),
                Application.of("command seq",
                               (typecheck_return(env, head, possibly_void_type),
                                typecheck_return_seqs(updated_env, tail, typ)),
                               focus=focus)
            )
        case _:
            return typecheck_return(env, stmts, typ)


@fixpoint(lambda: EmptyType())
def parse_type(type_expression: TreeGrammar) -> Type:
    """"WARNING: ONLY INVOKE THIS FUNCTION ON COMPLETELY PARSED TREEGRAMMARS"""
    match type_expression:
        case Token(token_type="numbertype"):
            return NUMBERTYPE
        case Token(token_type="stringtype"):
            return STRINGTYPE
        case Token(token_type="booltype"):
            return BOOLEANTYPE
        case Application("0-ary functype", (return_type,)):
            return FuncType.of(VOIDTYPE, parse_type(return_type))
        case Application("n-ary functype", (arg_types, return_type)):
            return FuncType.of(parse_type_seq(arg_types),
                               parse_type(return_type))
    raise ValueError(f"Unexpected type expression {type_expression}")


@fixpoint(lambda: VOIDTYPE)
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
    @fixpoint(lambda: VOIDTYPE)
    def infer_type_expression_helper(exp: TreeGrammar) -> Type:
        match exp:
            case Token(token_type="int"):
                return NUMBERTYPE
            case Token(token_type="str"):
                return STRINGTYPE
            case Token(token_type="true"):
                return BOOLEANTYPE
            case Token(token_type="false"):
                return BOOLEANTYPE
            case Token(token_type="id", prefix=prefix):
                return env._get_typed(prefix, TopType())[1]
            case Application("0-ary app", (func,)):
                functype = infer_type_expression_helper(func)
                if isinstance(functype, FuncType):
                    return functype.return_type
                elif isinstance(functype, EmptyType):
                    return EmptyType()
                raise ValueError(f"Unexpected type {functype} for function {func}")
            case Application("n-ary app", (func, args)):
                functype = infer_type_expression_helper(func)
                args_type = infer_type_args(env, args)
                if isinstance(functype, FuncType) and args_type in functype.params:
                    return functype.return_type
                return EmptyType()
            case Application("grp", (exp_inner,)):
                return infer_type_expression_helper(exp_inner)
            case Application(op, (_, _)) if op in BINOP:
                if op in BINOP_INT_INT_TO_INT:
                    return NUMBERTYPE
                if op in BINOP_INT_INT_TO_BOOL or op in BINOP_BOOL_BOOL_TO_BOOL:
                    return BOOLEANTYPE
            case Application("ternary expression", (then_val, _, else_val)):
                then_type = infer_type_expression_helper(then_val)
                else_type = infer_type_expression_helper(else_val)
                return (then_type if then_type == else_type else EmptyType())
            case Union(children):
                types = {infer_type_expression_helper(child) for child in children
                         }.difference({EmptyType()})
                if len(types) != 1:
                    raise ValueError(f"Unexpected type(s) {types} for expression {exp}")
                return types.pop()
            case _:
                # TODO: Fixpoint shouldn't evaluate the function on unneeded children.
                # I'd prefer to throw an error in this case, but I can't.
                return EmptyType()
    if env not in infer_type_expression_helper_functions:
        infer_type_expression_helper_functions[env] = infer_type_expression_helper
    return infer_type_expression_helper_functions[env](exp)


infer_type_agrs_helper_functions: dict[Environment, Callable] = dict()


def infer_type_args(env: Environment, args: TreeGrammar) -> Type:
    @fixpoint(lambda: VOIDTYPE)
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


infer_return_type_helper_functions: dict[Environment, Callable] = dict()


# def infer_return_type(env: Environment, stmts: TreeGrammar) -> Type:
#     """WARNING: DO NOT CALL ON INCOMPLETE TREEGRAMMAR."""
#     @fixpoint(lambda: VOIDTYPE)
#     def infer_return_type_helper(stmt: TreeGrammar) -> Type:
#         match stmt:
#             case EmptySet():
#                 return EmptyType()
#             case Union(children):
#                 updates = {infer_return_type(env, child) for child in children
#                            }.difference({EmptyType()})
#                 if len(updates) == 1:
#                     return updates.pop()
#                 if len(updates) > 1:
#                     raise ValueError(f"infer_return_type got ambiguous stmts {stmt}")
#                 return EmptyType()
#             case Application("return statement", (ret_val,)):
#                 return infer_type_expression(env, ret_val)
#             case Application("nonempty block", (body,)):
#                 return infer_return_type_seq(env, body)
#             case Application("for loop", (init, _, _, body)):
#                 updated_env = env.add(get_new_bindings(init))
#                 return infer_return_type(updated_env, body)
#             case Application("if-then-else", (_, then_branch, else_branch)):
#                 then_type = infer_return_type_helper(then_branch)
#                 else_type = infer_return_type_helper(else_branch)
#                 return (then_type if then_type == else_type else EmptyType())
#             case _:
#                 return VOIDTYPE
#     if env not in infer_return_type_helper_functions:
#         infer_return_type_helper_functions[env] = infer_return_type_helper
#     return infer_return_type_helper_functions[env](stmts)


# infer_return_type_seq_helper_functions: dict[Environment, Callable] = dict()


# def infer_return_type_seq(env: Environment, stmts: TreeGrammar) -> Type:
#     """WARNING: DO NOT CALL ON INCOMPLETE TREEGRAMMAR."""
#     @fixpoint(lambda: EmptyType())
#     def infer_return_type_seq_helper(stmt_seq: TreeGrammar) -> Type:
#         match stmt_seq:
#             case EmptySet():
#                 return EmptyType()
#             case Union(children):
#                 updates = {infer_return_type_seq(env, child) for child in children
#                            }.difference({EmptyType()})
#                 if len(updates) == 1:
#                     return updates.pop()
#                 if len(updates) > 1:
#                     raise ValueError(f"infer_return_type_seq "
#                                       + "got weird stmts {stmt_seq}")
#                 return EmptyType()
#             case Application("command seq", (head, tail)):
#                 head_typ = infer_return_type(env, head)
#                 if head_typ != VOIDTYPE:
#                     return head_typ
#                 updated_env = env.add(get_new_bindings(head))
#                 return infer_return_type_seq(updated_env, tail)
#             case _:
#                 return infer_return_type(env, stmt_seq)
#     if env not in infer_return_type_seq_helper_functions:
#         infer_return_type_seq_helper_functions[env] = infer_return_type_seq_helper
#     return infer_return_type_seq_helper_functions[env](stmts)


@fixpoint(lambda: tuple())
def get_new_bindings(stmt: TreeGrammar) -> tuple[tuple[str, Type, bool], ...]:
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
            return ((get_identifier_name(var), parse_type(type), True),)
        case Application("const declaration", (var, type, _)):
            return ((get_identifier_name(var), parse_type(type), False),)
        case Application("0-ary func decl", (func, return_type, _)):
            return ((get_identifier_name(func),
                     FuncType.of(VOIDTYPE, parse_type(return_type)),
                     False),)
        case Application("n-ary func decl", (func, params, return_type, _)):
            return ((get_identifier_name(func),
                     FuncType.of(type_of_params(params), parse_type(return_type)),
                     False),)
        case Application("param sequence", (head, tail)):
            return get_new_bindings(head) + get_new_bindings(tail)
        case Application("typed_id", (var, type_signature)):
            return ((get_identifier_name(var), parse_type(type_signature), True),)
        case _:
            return tuple()


@fixpoint(lambda: "")
def get_identifier_name(exp: TreeGrammar) -> str:
    """WARNING: DO NOT CALL ON INCOMPLETE TREEGRAMMAR."""
    match exp:
        case Token(token_type="id", prefix=prefix):
            return prefix
    raise ValueError(f"Unexpected identifier {exp}")


@fixpoint(lambda: VOIDTYPE)
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


default_env = Environment.from_dict({
    "Math.PI": NUMBERTYPE,
    "Math.pow": FuncType.of(ProdType.of(NUMBERTYPE, NUMBERTYPE), NUMBERTYPE),
    "Math.log2": FuncType.of(ProdType.of(NUMBERTYPE), NUMBERTYPE),
    "Math.sqrt": FuncType.of(ProdType.of(NUMBERTYPE), NUMBERTYPE),
    "Math.floor": FuncType.of(ProdType.of(NUMBERTYPE), NUMBERTYPE),
    "Math.ceil": FuncType.of(ProdType.of(NUMBERTYPE), NUMBERTYPE),
    "Math.clz32": FuncType.of(ProdType.of(NUMBERTYPE), NUMBERTYPE),
    # Min and max types are slightly imprecise, but whatever
    "Math.min": FuncType.of(ProdType.of(NUMBERTYPE, extensible=True), NUMBERTYPE),
    "Math.max": FuncType.of(ProdType.of(NUMBERTYPE, extensible=True), NUMBERTYPE),
})

typescript_checker = RealizabilityChecker(
    lambda asts: typecheck_return_seqs(default_env, asts, VOIDTYPE),
    codeblocks(),
    lexer_spec,
)
