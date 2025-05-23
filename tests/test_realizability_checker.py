from core.grammar import Application, Constant, EmptySet, TreeGrammar, Union
from core.parser import Choice, Concatenation, ConstantParser
from core.rewrite import rewrite
from runllm.constrained_decoding import RealizabilityChecker


@rewrite
def identity(t: TreeGrammar):
    return t


@rewrite
def even_val(t: TreeGrammar):
    match t:
        case EmptySet():
            return EmptySet()
        case Constant(c):
            if c % 2 == 0:
                return Constant(c)
            else:
                return EmptySet()
        case Application("+", children):
            return Union.of(
                Application.of("+", even_val(children[0]), even_val(children[1])),
                Application.of("+", odd_val(children[0]), odd_val(children[1]))
            )
        case Union(children):
            return Union.of(
                *[even_val(c) for c in children]
            )
        case _:
            raise TypeError(f"Unexpected type: {type(t)}")


@rewrite
def odd_val(t: TreeGrammar):
    match t:
        case EmptySet():
            return EmptySet()
        case Constant(c):
            if c % 2 == 1:
                return Constant(c)
            else:
                return EmptySet()
        case Application("+", children):
            return Union.of(
                Application.of("+", even_val(children[0]), odd_val(children[1])),
                Application.of("+", odd_val(children[0]), even_val(children[1]))
            )
        case Union(children):
            return Union.of(
                *[odd_val(c) for c in children]
            )
        case _:
            raise TypeError(f"Unexpected type: {type(t)}")


@rewrite
def parse_E():
    return Choice.of(
        ConstantParser(1),
        Concatenation.of(
            "+",
            ConstantParser(1),
            ConstantParser("+"),
            parse_E(),
            rearrange=(0, 2)
        )
    )

class TestRealizabilityChecker:
    # TODO: Add a sensible lexer once we have an implementation
    # Make sure it has an end of string symbol from the tokenizer

    eos_symbol = "eos"

    def test_gcd(self):
        chk = RealizabilityChecker(
            constraint=identity,
            initial_grammar=parse_E,
            image=identity,
            lexer=None
        )

        assert chk.realizable("1 + 1 + 1")
        assert not chk.realizable("1 + 1 + 2")
        assert chk.realizable("")
        assert chk.realizable("  ")
        assert not chk.realizable(" +")
        assert chk.realizable("1")

    def test_evenval(self):
        chk = RealizabilityChecker(
            constraint=even_val,
            initial_grammar=parse_E,
            image=identity,
            lexer=None
        )

        assert not chk.realizable("1 + 1 + 1" + TestRealizabilityChecker.eos_symbol)
        assert chk.realizable("1 + 1 + 1")
        assert not chk.realizable("1 + 1 + 2")
        assert chk.realizable("")
        assert chk.realizable("  ")
        assert not chk.realizable(" +")
        assert chk.realizable("1 + 1" + TestRealizabilityChecker.eos_symbol)