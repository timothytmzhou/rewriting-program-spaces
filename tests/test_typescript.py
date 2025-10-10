from functools import reduce
from core.grammar import is_nonempty
from core.lexing.lexing import lex, partial_lex
from core.parser import D, Choice, delta, image
from llm.realizability import RealizabilityChecker
from tests.utils import reset
from experiments.typescript.environment import *
from experiments.typescript.types import *
from experiments.typescript.typescript_abstract_syntax import (common_lexer_specs,
                                                               common_parsers)
from experiments.typescript.typescript_typechecker import (
    typeprune_expression,
    typeprune_return_seqs,
    typescript_typechecker
)

ts_expression_grammar_checker = RealizabilityChecker(
    lambda x: x,
    common_parsers["exp"],
    common_lexer_specs["exp"],
)

ts_command_grammar_checker = RealizabilityChecker(
    lambda x: x,
    common_parsers["command_seq"],
    common_lexer_specs["command_seq"],
)


def type_expression_test(pref: str, envs: Environment = Environment(),
                         typ: Type = TopType(), final: bool = False) -> bool:
    """
    Returns the type of the expression.
    """
    if not final:
        lexes = partial_lex(pref, common_lexer_specs["exp"])
    else:
        lexes = lex(pref, common_lexer_specs["exp"])

    # Build term representing set of possible parse trees
    terms = [reduce(lambda parser, leaf: D(leaf, parser), lex, common_parsers["exp"])
             for lex in lexes]
    derived_parser = Choice.of(terms) if not final else delta(Choice.of(terms))

    # Build corresponding set of good ASTs
    good_progs = typeprune_expression(envs, image(derived_parser), typ)

    # Check nonemptiness of term
    return is_nonempty(good_progs)


def type_commands_test(pref: str, envs: Environment = Environment(),
                       typ: Type = VOIDTYPE, final: bool = False) -> bool:
    """
    Returns the type of the expression.
    """
    if not final:
        lexes = partial_lex(pref, common_lexer_specs["command_seq"])
    else:
        lexes = lex(pref, common_lexer_specs["command_seq"])

    # Build term representing set of possible parse trees
    terms = [reduce(lambda parser, leaf: D(leaf, parser),
                    lex, common_parsers["command_seq"])
             for lex in lexes]
    derived_parser = Choice.of(terms) if not final else delta(Choice.of(terms))

    # Build corresponding set of good ASTs
    good_progs = typeprune_return_seqs(envs, image(derived_parser), typ)
    # Check nonemptiness of term
    return is_nonempty(good_progs)


@reset
def test_expression_grammar():
    assert ts_expression_grammar_checker.realizable("")
    assert ts_expression_grammar_checker.realizable("5 + 16")
    assert ts_expression_grammar_checker.realizable("albatross")
    # assert ts_expression_grammar_checker.realizable("\"\"")
    # assert ts_expression_grammar_checker.realizable("((a:number, b:string) => a + \"")
    # assert ts_expression_grammar_checker.realizable("foo.bar.baz + bar(foo, 18)")
    assert not ts_expression_grammar_checker.realizable("5 + 10;")
    assert not ts_expression_grammar_checker.realizable("/16")
    # assert not ts_expression_grammar_checker.realizable("if (h == 10) then {l")
    assert not ts_expression_grammar_checker.realizable("foo(,)")
    assert not ts_expression_grammar_checker.realizable(")")
    assert ts_expression_grammar_checker.realizable("""//hello joe
    5""")


@reset
def test_command_grammar():
    assert ts_command_grammar_checker.realizable("")
    assert ts_command_grammar_checker.realizable("5 + 16")
    assert ts_command_grammar_checker.realizable("5 + 16;")
    assert ts_command_grammar_checker.realizable("retu")
    assert ts_command_grammar_checker.realizable(
        "{return alpha; return beta; {}")
    assert not ts_command_grammar_checker.realizable("}")
    assert not ts_command_grammar_checker.realizable("return return ")
    assert not ts_command_grammar_checker.realizable("function false ")
    assert not ts_command_grammar_checker.realizable("foo(,)")
    assert not ts_command_grammar_checker.realizable(";")


@reset
def test_typechecking_expression():
    assert type_expression_test("")
    assert type_expression_test("789 ")
    assert type_expression_test("-789 ")
    assert type_expression_test("- ")
    assert type_expression_test("5 + 9 == 4 ")
    assert type_expression_test("5 - 9 === 4 / 7 ")
    assert type_expression_test("5 != 4 % 4")
    assert type_expression_test("5 != 4.8 % 7.3 + 6")
    assert type_expression_test("true || false && 6 !== 8 + ")
    assert type_expression_test("true || false && 6 >= 8 + 9 ? 5 : ")
    assert type_expression_test("(4.8 > 7.0 + 0.3)")
    assert type_expression_test("4.8 > 7.0 + 0.3 ? 5")
    assert type_expression_test("(5 <= 4.8 ? false : true) ? 4.8  : 6")
    assert type_expression_test("5 < 6 ? 4.8 + 7", typ=NUMBERTYPE)
    assert type_expression_test("false")
    assert type_expression_test("bar",
                                envs=Environment.from_dict({"bar": TopType()}))
    assert type_expression_test("bar",
                                envs=Environment.from_dict(
                                    {"bar": NumberType()}),
                                typ=NumberType())
    assert type_expression_test("bar",
                                envs=Environment.from_dict(
                                    {"barre": NumberType()}),
                                typ=NumberType())
    assert type_expression_test("5 + 16", typ=NumberType())
    assert type_expression_test("((5 + 16))", typ=NumberType())
    assert type_expression_test("foo()",
                                envs=Environment.from_dict({"foo": FuncType(
                                    VOIDTYPE,
                                    return_type=BooleanType()
                                )}),
                                typ=BooleanType())
    assert type_expression_test("foo(1, 6)",
                                envs=Environment.from_dict({"foo": FuncType(
                                    ProdType.of(NUMBERTYPE, NUMBERTYPE),
                                    return_type=BooleanType()
                                )}),
                                typ=BooleanType())
    assert type_expression_test("foo",
                                envs=Environment.from_dict({"foo": FuncType(
                                    VOIDTYPE,
                                    return_type=BooleanType()
                                )}),
                                typ=BooleanType())
    assert not type_expression_test(".5")
    assert not type_expression_test("--")
    assert not type_expression_test("6 || ")
    assert not type_expression_test("0.6 && ")
    assert not type_expression_test("5 ? 4.8 + 7.0 : 6")
    assert not type_expression_test("5 ? 4.8 + 7.0 : true")
    assert not type_expression_test("5 ? 4.8 + 7 : 6", typ=STRINGTYPE)
    assert not type_expression_test("5 ? 4.8 + 7", typ=BOOLEANTYPE)
    assert not type_expression_test("bar")
    assert not type_expression_test("bar",
                                    envs=Environment.from_dict(
                                        {"bar": BooleanType()}),
                                    typ=StringType())
    assert not type_expression_test("foo()",
                                    envs=Environment.from_dict({"foo": FuncType(
                                        VOIDTYPE,
                                        return_type=NumberType()
                                    )}),
                                    typ=StringType())
    assert type_expression_test("foo ",
                                envs=Environment.from_dict({"foo": FuncType(
                                    VOIDTYPE,
                                    return_type=BooleanType()
                                )}),
                                typ=BooleanType())
    assert type_expression_test("(17 + 12 * 8 == 16)", typ=BooleanType())
    assert not type_expression_test("foobar()",
                                    envs=Environment.from_dict({"foo": FuncType(
                                        VOIDTYPE,
                                        return_type=BooleanType()
                                    )}),
                                    typ=BooleanType())
    assert not type_expression_test("5 + 16", typ=StringType())
    assert not type_expression_test("(((5 + 16)))", typ=StringType())
    assert not type_expression_test("5 + true", typ=NumberType())
    assert not type_expression_test("/16")
    assert not type_expression_test("if (h == 10) then {l")
    assert not type_expression_test("foo(,)")
    assert not type_expression_test(")")


@reset
def test_simple_statements():
    assert type_commands_test("")
    assert type_commands_test("{}")
    assert type_commands_test("{{}}")
    assert type_commands_test("5;")
    assert type_commands_test("5;17")
    assert type_commands_test("{5;17")
    assert type_commands_test("{} {}")
    assert type_commands_test("{5;17;} {}")

    assert not type_commands_test("}")
    assert not type_commands_test(";")
    assert not type_commands_test("5;+17")
    assert not type_commands_test("{5;17;};16;")


@reset
def test_simple_returns():
    assert not type_commands_test("return ")
    assert not type_commands_test("{return ")
    assert not type_commands_test("5; {6 + 12; return ")


@reset
def test_simple_0_ary_func_decls():
    assert type_commands_test("function foo (")
    assert type_commands_test("function foo (): number { ")
    assert type_commands_test("function foo (): number {return 5;} ")
    assert type_commands_test("function foo (): boolean {18; 47; {} return 5 ")
    assert type_commands_test(
        "function foo (): number {18; 47; {} return 5 + 12;} ")
    assert type_commands_test("""function foo (): number {18; 47; {} return 5+12;}
                               foo() + foo()""")
    assert type_commands_test(
        "function foo () : boolean {18; 47; {} return 5 + ")
    assert type_commands_test(
        "function foo () : number {18; 47; {} return 5 > ")


@reset
def test_simple_n_ary_func_decls():
    assert type_commands_test("function foo (x")
    assert type_commands_test("function foo (x: num")
    assert type_commands_test("function foo (x: number")
    assert type_commands_test("function foo (x: number) : numbe")
    assert type_commands_test("function foo (x: number) : number {")
    assert type_commands_test("function foo (x: number) : number {x;")
    assert type_commands_test(
        "function foo (x: number) : number {x; return x + 100;}")
    assert type_commands_test("""function foo (x: number, b: boolean) : number
                              {b; {{x;}} return x + 100;}""")
    assert type_commands_test("""function foo (x: number) : number {
                                    return x;
                              }
                              foo(1);""")
    assert type_commands_test("""function foo (x: number, b: boolean) : number {
                                    return x + 100;
                              }
                              foo(1, true);""")
    assert type_commands_test("""function foo (x: number, s: boolean) : number {
                                    return x;
                              }
                              foo(1, false);""")
    assert type_commands_test("""function foo (x: number, s: boolean) : number {
                                    return x;
                              }
                              foo(foo(10, 1 == 1), 0 !== 1);""")
    assert type_commands_test("""function foo (x: number, b: boolean) : number {
                                    return - x + 100;
                              }
                              function bar (x: number, b: boolean) : number {
                                    return - foo(x, b);
                              }""")

    assert not type_commands_test("function foo (x: number) : number {x;}")
    assert not type_commands_test("function foo (x) : number {x;}")
    assert not type_commands_test(
        "function foo (x: number) : boolean {return x;}")
    assert not type_commands_test("""function foo (x: number, boo: boolean) : number {
                                    return x;
                              }
                              foo(5 == 17, true);""")


@reset
def test_lets():
    assert type_commands_test("let x: number = 5;")
    assert type_commands_test("let x: number = 5; x = 7")
    assert type_commands_test("let x: number = 5; x += ")
    assert type_commands_test("let x: number = 5; x -= ")
    assert type_commands_test("let x: number = 5; x *= ")
    assert type_commands_test("let x: number = 5; x /= ")
    assert type_commands_test("let x: number = 5; x ++ ")
    assert type_commands_test("let x: number = 5; x -- ")
    assert type_commands_test("let x= 5; -- x")
    assert type_commands_test("const x: number = 5; let y: boolean = true;")
    assert type_commands_test("const x = 5; let y = true;")
    assert type_commands_test("const x: number = 5; let y: boolean = x")
    assert type_commands_test(
        "const x: number = 5; let y: boolean = true; x + 17;")
    assert type_commands_test("let x: number = 5; let y: boolean = tr")
    assert type_commands_test("function foo (x: number) : number {return 0;}"
                              + "let x: (a: number) => number = ")
    assert type_commands_test("function foo (x: (a: number, b: boolean) => number)"
                              + "")
    assert type_commands_test("let x: number = 5; let y: boolean = 6")
    assert type_commands_test("function foo (x: number) : number "
                              + "{let y:number = x; return y;}")
    assert type_commands_test("let x: number = 5; x = (7 ==")
    assert not type_commands_test("const x: number = 5; x = 7")
    assert not type_commands_test("const x = 5; x ++ ")
    assert not type_commands_test("const x: number = 5; x += ")
    assert not type_commands_test("const x: number = 5; x ++ ")
    assert not type_commands_test("const x: number = 5; ++ x")
    assert not type_commands_test("let x: number = z; let y: boolean = true")
    assert not type_commands_test("x = 7; x += ")
    assert not type_commands_test(
        "let x: number = true; let y: boolean = true")
    assert not type_commands_test("let x: number = 5; let y: boolean = 6;")
    assert not type_commands_test("function foo (x: number) : number {"
                                  + "let y:bool = 5; return y;}")
    assert not type_commands_test("function foo (x: number) : number {"
                                  + "let y:bool = true; return y;}")
    assert not type_commands_test("""
                                    const dp: number = 0;
                                    for (let i: number = 0; i < 10; i++) {
                                        dp = """)
    assert not type_commands_test("let x: (a: number) => number = ")
    assert not type_commands_test(
        "let x: (a: number, b: boolean) => number = ")


@reset
def test_recursion():
    assert type_commands_test("""function foo () : number {
                                    return foo();
                              }
                              foo();""")
    assert type_commands_test("""function foo (x: number) : number {
                                    return foo(x + 1);
                              }
                              foo(5);""")
    assert type_commands_test("""function foo (x: number) : number {
                                    return foo """)
    assert type_commands_test("""function foo (x: number) : number {
                                    return foo(x + 1);
                              }
                              function bar (x: number) : number {
                                    return foo(x + bar(1));
                              }""")
    assert not type_commands_test("""function foo (x: number) : number {
                                        return bar(x + 1);
                                  }
                                  function bar (x: number) : boolean {
                                        return foo(x + 1);
                                  }""")


@reset
def test_for_loops():
    assert type_commands_test("for (let i: nu")
    assert type_commands_test("for (let i: number = 0; i")
    assert type_commands_test("for (let i: number = 0; true; i++) { }")
    assert type_commands_test(
        "for (let i: number = 0; i < 10; i=9) { i + 1; }")
    assert type_commands_test("for (let i: number = 0; (17 + 12 * 8 == 16); i+=9) "
                              + "{ i + 1; }")
    assert type_commands_test("for (let i: boolean = true; i; i = false) "
                              + "{ let j: number = 1; }")
    assert type_commands_test("for (let i: number = 0; i < 10; i++)"
                              + " { let j: number = i + 1; }")
    assert type_commands_test("for (let i: number = 0; i < 10; i++) "
                              + "{ let j: number = i + 1; }")
    assert not type_commands_test("for let i: number = 0; i < 10; i++) { }")
    assert not type_commands_test("for (let i: number = 0; i + 10; i++) { }")
    assert not type_commands_test("for (let i: boolean = true; i < 10; i = false) "
                                  + "{ let j: number = 1; }")
    assert not type_commands_test("for (let i: boolean = true; i ; i += 4) "
                                  + "{ let j: number = 1; }")
    assert not type_commands_test("for (i = 0; true ; i++) { }")


@reset
def test_conditionals():
    assert type_commands_test("if (true) {} else {}")
    assert type_commands_test("""function foo (x: number) : number {
                                    if (x > 10){
                                        x = 0;
                                    } else {}
                                    return x;
                              }
                              function bar (x: number, y: number) : number {
                                    if (x > 10){
                                        x = 0;
                                    } else {}
                                    return x;
                              }
                              if (true) {
                                foo(1);
                                bar(8, foo(bar(1,
                              """)
    assert type_commands_test("let x: number = 0; "
                              + "if (true) {x++;} else {x=7;}")
    assert type_commands_test("""function foo (x: number) : number {
                                    if (x > 10){
                                        x = 0;
                                    } else {}
                                    return x;
                              }""")
    assert type_commands_test("""function foo (x: number) : boolean {
                                    if (x > 10){
                                        return false;
                                    } else {
                                        return true;
                                    }
                              }""")
    assert type_commands_test("""function foo (x: number) : boolean {
                                    if (x > 10 && x <= 1.7){
                                        {13; {return false;}}
                                    } else {
                                        return true;
                                    }
                              }
                              foo(5);""")
    assert type_commands_test("""function log_2 (x: number) : number {
                                    if (x > 2){
                                        let y : number = log_2(x/2);
                                        return y + 1;
                                    } else {
                                        if (x > 2) {
                                            let y : number = log_2(x/2);
                                            return y + 1;
                                        } else {
                                            return 0;
                                        }
                                    }
                              }
                              log_2(8);""")
    assert type_commands_test("""function foo (x: number) : boolean {
                                    if (x > 10){
                                        retu""")
    assert type_commands_test("""function foo (x: number) : boolean {
                                    if (x > 10){
                                        return false;
                                    } els""")
    assert type_commands_test("""function foo (x: number) : boolean {
                                    if (x > 10){
                                        return false;
                                    } else {
                                        return 8""")
    assert not type_commands_test("if (18 + 6) {} else {}")
    assert not type_commands_test("if (true) {} else {return ")
    assert not type_commands_test("""function foo (x: number) : boolean {
                                    if (x > 10){
                                        return 6;""")
    assert not type_commands_test("if (true) {} else {return ")
    assert not type_commands_test("""function pow (x: number) : number {
                                    if (x > 2){
                                        let y : number = pow(x/2);
                                        return y + 1;
                                    } else {
                                        if (x > 2) {
                                            let y : number = pow(x/2);
                                            return y + 1;
                                        } else {
                                            return 0 !== 9;
                                        }
                                    }
                              }
                              pow(8);""")


@reset
def test_final():
    assert type_commands_test("""
                              function power(a: number, b: number): number {
                                return Math.pow(a, b);
                              }""",
                              envs=Environment(FrozenDict(
                                  (
                                      ("Math.pow",
                                       FuncType.of(ProdType.of(NUMBERTYPE, NUMBERTYPE),
                                                   NUMBERTYPE)),
                                  ))
                              ),
                              final=True)

    assert not type_commands_test("""function foo (x: number) : boolean {
                                    if (x > 10){
                                        retu""", final=True)


@reset
def test_possibly_void_return_types():
    assert type_commands_test("""function foo(a: number, b: number): number {
                                for (let x: number = 0; x < 10; x++) {
                                    return a % b;
                                }
                                return 0;
                              }""")
    assert type_commands_test("""function foo(a: number, b: number): number {
                                if (a < 10) {
                                    return a - b;
                                } else{
                                    a *= 2;
                                }
                                return a;
                              }""")
    assert type_commands_test("""function foo(a: number, b: number): number {
                                if (a < 10) {
                                    return a - b;
                                } else{
                                    a *= 2;
                                }
                               """)

    assert not type_commands_test("""function foo(a: number, b: number): number {
                                for (let x: number = 0; x < 10; x++) {
                                    return a + b;
                                }
                              }""")

    assert not type_commands_test("""function foo(a: number, b: number): number {
                                if (a < 10) {
                                    return a + b;
                                } else {
                                    a *= 2;
                                }
                              }""")


@reset
def test_if_then():
    assert type_commands_test("if (true) {5;} 6")
    assert type_commands_test("""function foo (x: number) : boolean {
                                    if (x > 10){
                                        return false;
                                    }
                                    ret""")
    assert type_commands_test("""function foo (x: number) : number {
                                    for (let i: number = 0; i < 10; i = i) {
                                        if (x > 10){
                                                return 6;
                                            }
                                    }""")
    assert not type_commands_test("if (true) {return 7;} 6;")
    assert not type_commands_test("""function foo (x: number) : boolean {
                                    if (x > 10){
                                        return 6;
                                    }
                                    ret""")
    assert not type_commands_test("""function foo (x: number) : number {
                                    if (x > 10){
                                        return 6;
                                    }
                                }""")
    assert not type_commands_test("""function foo (x: number) : number {
                                    for (const i: number = 0; i < 10; i = i) {
                                        if (x > 10){
                                                return 6;
                                            }
                                    }
                                }""")
    assert not type_commands_test("""function foo (x: number) : number {
                                    for (const i: number = 0; i < 10; i = i) {
                                        if (x > 10){
                                                return 6;
                                            }
                                    }""")


@reset
def test_while():
    assert type_commands_test("""
                                while
                                """)
    assert type_commands_test("""
                                while (true) {
                                """)
    assert type_commands_test("""
                                while (9 < 10) {}
                                """)
    assert type_commands_test("""
                                let b: number = 0;
                                while (b < 10) {8;16;{}}
                                """)
    assert type_commands_test("""
                                let b: number = 0;
                                while (b < 10) {8;16;{}}
                                """)
    assert type_commands_test("""function foo (x: number) : number {
                                    while (x > 10){
                                        return 6;
                                    }
                                """)
    assert type_commands_test("""function foo (x: number) : number {
                                    while (x > 10){
                                        return 6;
                                    }
                                    return 0;
                              }""")
    assert not type_commands_test("""function foo (x: number) : number {
                                    while (x > 10){
                                        return 6;
                                    }
                                }""")
    assert not type_commands_test("""function foo (x: number) : number {
                                    while (x > 10){
                                        return f
                                """)


@reset
def test_codeblock():
    assert type_commands_test("""
                                function
                                """)
    assert typescript_typechecker.realizable("""
                                         ```
                                         function
                                         """)
    assert typescript_typechecker.realizable("""
                                         ```
                                         function foo (x: number) : number {
                                            for (let i: number = 0; i < 10; i = i) {
                                                if (x > 10){
                                                    return 6;
                                                }
                                            }
                                            return 0;
                                        }
                                         ```
                                         """)


# # Enable test if you will allow "```typescript" to begin a codeblock.
# @reset
# def test_typescript_codeblock_prefix():
#     assert typescript_typechecker.realizable("""
#                                          ```typescript
#                                          function
#                                          """)
#     assert not typescript_typechecker.realizable("""
#                                          ```tpescript
#                                          function
#                                          """)


@reset
def test_min_max():
    assert typescript_typechecker.realizable("""
        ```
        function min(a: number, b: number): number {
            return Math.min(5, 3);
        }```""")


@reset
def test_old_errors():
    assert type_commands_test("let x = 5 / 19; x + 16;")
    assert type_commands_test("""function foo (x: number) : number {
                                    if (x > 10){
                                        x = 0;
                                    } else {}
                                    return x;
                              }
                              function bar (x: number, y: number) : number {
                                    if (x > 10){
                                        x = 0;
                                    } else {}
                                    return x;
                              }
                              true ? bar(1, foo(0))
                              """)
    assert not typescript_typechecker.realizable("""
        ```
        let memoizationTable: number = (1024 * 576); // Initialize table size as maximum sequence length times max value divided by step size + 1
        memoizationTable = Math.floor((Math.pow(3,(memoizationTable - 1)) % ((Math.pow(89,m)
    """)
    assert ts_expression_grammar_checker.realizable("""
                                  5 ? (0 % 3 == 0 ? (((((((((((((((5 + 3) + 9) + 1) + 0) + 5) + 9) + 1) + 0) + 5) + 9) + 1) + 0) + 5) + 9) + 1)"""
                                                    )
    assert not typescript_typechecker.realizable("""
                                  ```
                                  function is_nonagonal(n: number): boolean {
                                      const numDigits: number = (n * Math.log2(10)) / Math.log2(3);
                                      if (numDigits === Math.floor(numDigits)) {
                                          let digits: number = 0;
                                          while (n > 0) {
                                              digits = (digits ? (n % 3 == 0 ? 0 + (n - 3) / 9 + 1 + 0 + n % 9 + 1 + 0 + n % 9 + 1 + 0 + n % 9 + 1"""
                                                 )


# Slow test that uses niche behavior for prod types.
@reset
def test_niche_failure_mode():
    unconstrained_output = """  ```
function getMaxSum(n: number): number {
    if (n <= 0) {
        return 0;
    } else if (n === 1 || n === 2 || n === 3 || n === 4 || n === 5) {
        return n;
    } else {
        const halfN = Math.floor(n / 2);
        const thirdN = Math.floor(n / 3);
        const quarterN = Math.floor(n / 4);
        const fifthN = Math.floor(n / 5 """
    for i in range(len(unconstrained_output)):
        print(i)
        assert typescript_typechecker.realizable(unconstrained_output[:i])
