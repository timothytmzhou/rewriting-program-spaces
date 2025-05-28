from lexing.lexing import *
from lexing.leaves import EPS, RegexLeaf
import greenery as grn


def test_partial_lex_abc():
    lspec = LexerSpec({
        RegexLeaf("a", grn.parse("a")),
        RegexLeaf("b", grn.parse("b")),
        RegexLeaf("c", grn.parse("c"))
    }, grn.parse(""))
    assert partial_lex("abc", lspec) == {
        (RegexLeaf("a", EPS, "a"),
         RegexLeaf("b", EPS, "b"),
         RegexLeaf("c", EPS, "c"))}

    assert partial_lex("", lspec) == {()}
    assert partial_lex("d", lspec) == set()


def test_partial_lex_ignore():
    lspec = LexerSpec({
        RegexLeaf("a", grn.parse("a")),
        RegexLeaf("b", grn.parse("b")),
        RegexLeaf("c", grn.parse("c"))
    }, grn.parse("\\s+"))
    assert partial_lex("a b   c", lspec) == {
        (RegexLeaf("a", EPS, "a"),
         RegexLeaf("b", EPS, "b"),
         RegexLeaf("c", EPS, "c"))}

    assert partial_lex("    ", lspec) == {()}


def test_partial_lex_disjoint():
    lspec = LexerSpec({
        RegexLeaf("a", grn.parse("a+")),
        RegexLeaf("b", grn.parse("b+")),
    }, grn.parse(""))
    assert partial_lex("aaaa", lspec) == {
        (RegexLeaf("a", grn.parse("a*"), "aaaa"),)}

    assert partial_lex("aaabaabb", lspec) == {
        (RegexLeaf("a", EPS, "aaa"),
         RegexLeaf("b", EPS, "b"),
         RegexLeaf("a", EPS, "aa"),
         RegexLeaf("b", grn.parse("b*"), "bb"))}

    assert partial_lex("", lspec) == {()}


def test_partial_lex_nonsingleton():
    lspec = LexerSpec({
        RegexLeaf("print", grn.parse("print$")),
        RegexLeaf("lpar", grn.parse("\\(")),
        RegexLeaf("rpar", grn.parse("\\)")),
        RegexLeaf("var", grn.parse("[a-z]+")),
        RegexLeaf("dot", grn.parse("\\.")),
        RegexLeaf("caps", grn.parse("tocaps"))
    }, grn.parse("\\s+"))
    assert partial_lex("print$( foo.tocap", lspec) == {
        (RegexLeaf("print", EPS, "print$"),
         RegexLeaf("lpar", EPS, "("),
         RegexLeaf("var", EPS, "foo"),
         RegexLeaf("dot", EPS, "."),
         RegexLeaf("caps", grn.parse("s"), "tocap")),
        (RegexLeaf("print", EPS, "print$"),
         RegexLeaf("lpar", EPS, "("),
         RegexLeaf("var", EPS, "foo"),
         RegexLeaf("dot", EPS, "."),
         RegexLeaf("var", grn.parse("[a-z]*"), "tocap"))
    }

    assert partial_lex("  ))( zip prin", lspec) == {
        (RegexLeaf("rpar", EPS, ")"),
         RegexLeaf("rpar", EPS, ")"),
         RegexLeaf("lpar", EPS, "("),
         RegexLeaf("var", EPS, "zip"),
         RegexLeaf("print", grn.parse("t$"), "prin")),
        (RegexLeaf("rpar", EPS, ")"),
         RegexLeaf("rpar", EPS, ")"),
         RegexLeaf("lpar", EPS, "("),
         RegexLeaf("var", EPS, "zip"),
         RegexLeaf("var", grn.parse("[a-z]*"), "prin"))
    }

    assert partial_lex("  ))( zip prin ", lspec) == {
        (RegexLeaf("rpar", EPS, ")"),
         RegexLeaf("rpar", EPS, ")"),
         RegexLeaf("lpar", EPS, "("),
         RegexLeaf("var", EPS, "zip"),
         RegexLeaf("var", EPS, "prin"))
    }


def test_partial_lex_finalize():
    lspec = LexerSpec({
        RegexLeaf("print", grn.parse("print$")),
        RegexLeaf("var", grn.parse("[a-z]+"))
    }, grn.parse("\\s+"))
    assert partial_lex("a p", lspec) == {
        (RegexLeaf("var", EPS, "a"),
         RegexLeaf("var", grn.parse("[a-z]*"), "p")),
        (RegexLeaf("var", EPS, "a"),
         RegexLeaf("print", grn.parse("rint$"), "p"))
    }

    assert lex("a p", lspec) == {
        (RegexLeaf("var", EPS, "a"),
         RegexLeaf("var", EPS, "p"))
    }