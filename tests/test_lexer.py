from lexing.lexing import *
from lexing.leaves import RegexLeaf
import regex as re


def test_partial_lex_abc():
    lspec = LexerSpec({
        RegexLeaf("a", re.compile("a")),
        RegexLeaf("b", re.compile("b")),
        RegexLeaf("c", re.compile("c"))
    }, re.compile(""))
    assert partial_lex("abc", lspec) == {
        (RegexLeaf("a", re.compile("a"), "a"),
         RegexLeaf("b", re.compile("b"), "b"),
         RegexLeaf("c", re.compile("c"), "c"))}

    assert partial_lex("", lspec) == {()}
    assert partial_lex("d", lspec) == set()


def test_partial_lex_ignore():
    lspec = LexerSpec({
        RegexLeaf("a", re.compile("a")),
        RegexLeaf("b", re.compile("b")),
        RegexLeaf("c", re.compile("c"))
    }, re.compile("\\s+"))
    assert partial_lex("a b   c", lspec) == {
        (RegexLeaf("a", re.compile("a"), "a"),
         RegexLeaf("b", re.compile("b"), "b"),
         RegexLeaf("c", re.compile("c"), "c"))}

    assert partial_lex("    ", lspec) == {()}


def test_partial_lex_disjoint():
    lspec = LexerSpec({
        RegexLeaf("a", re.compile("a+")),
        RegexLeaf("b", re.compile("b+")),
    }, re.compile(""))
    assert partial_lex("aaaa", lspec) == {
        (RegexLeaf("a", re.compile("a+"), "aaaa"),)}

    assert partial_lex("aaabaabb", lspec) == {
        (RegexLeaf("a", re.compile("a+"), "aaa"),
         RegexLeaf("b", re.compile("b+"), "b"),
         RegexLeaf("a", re.compile("a+"), "aa"),
         RegexLeaf("b", re.compile("b+"), "bb"))}

    assert partial_lex("", lspec) == {()}


def test_partial_lex_nonsingleton():
    lspec = LexerSpec({
        RegexLeaf("print", re.compile(r'print\$')),
        RegexLeaf("lpar", re.compile("\\(")),
        RegexLeaf("rpar", re.compile("\\)")),
        RegexLeaf("var", re.compile("[a-z]+")),
        RegexLeaf("dot", re.compile("\\.")),
        RegexLeaf("caps", re.compile("tocaps"))
    }, re.compile("\\s+"))
    assert partial_lex("print$( foo.tocap", lspec) == {
        (RegexLeaf("print", re.compile(r'print\$'), "print$"),
         RegexLeaf("lpar", re.compile("\\("), "("),
         RegexLeaf("var", re.compile("[a-z]+"), "foo"),
         RegexLeaf("dot", re.compile("\\."), "."),
         RegexLeaf("caps", re.compile("tocaps"), "tocap")),
        (RegexLeaf("print", re.compile(r'print\$'), "print$"),
         RegexLeaf("lpar", re.compile("\\("), "("),
         RegexLeaf("var", re.compile("[a-z]+"), "foo"),
         RegexLeaf("dot", re.compile("\\."), "."),
         RegexLeaf("var", re.compile("[a-z]+"), "tocap"))
    }

    assert partial_lex("  ))( zip prin", lspec) == {
        (RegexLeaf("rpar", re.compile("\\)"), ")"),
         RegexLeaf("rpar", re.compile("\\)"), ")"),
         RegexLeaf("lpar", re.compile("\\("), "("),
         RegexLeaf("var", re.compile("[a-z]+"), "zip"),
         RegexLeaf("print", re.compile(r'print\$'), "prin")),
        (RegexLeaf("rpar", re.compile("\\)"), ")"),
         RegexLeaf("rpar", re.compile("\\)"), ")"),
         RegexLeaf("lpar", re.compile("\\("), "("),
         RegexLeaf("var", re.compile("[a-z]+"), "zip"),
         RegexLeaf("var", re.compile("[a-z]+"), "prin"))
    }

    assert partial_lex("  ))( zip prin ", lspec) == {
        (RegexLeaf("rpar", re.compile("\\)"), ")"),
         RegexLeaf("rpar", re.compile("\\)"), ")"),
         RegexLeaf("lpar", re.compile("\\("), "("),
         RegexLeaf("var", re.compile("[a-z]+"), "zip"),
         RegexLeaf("var", re.compile("[a-z]+"), "prin"))
    }


def test_partial_lex_finalize():
    lspec = LexerSpec({
        RegexLeaf("print", re.compile("print$")),
        RegexLeaf("var", re.compile("[a-z]+"))
    }, re.compile("\\s+"))
    assert partial_lex("a p", lspec) == {
        (RegexLeaf("var", re.compile("[a-z]+"), "a"),
         RegexLeaf("var", re.compile("[a-z]+"), "p")),
        (RegexLeaf("var", re.compile("[a-z]+"), "a"),
         RegexLeaf("print", re.compile("print$"), "p"))
    }

    assert lex("a p", lspec) == {
        (RegexLeaf("var", re.compile("[a-z]+"), "a"),
         RegexLeaf("var", re.compile("[a-z]+"), "p"))
    }
