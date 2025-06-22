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
        (RegexLeaf("a", re.compile("a"), "a", True),
         RegexLeaf("b", re.compile("b"), "b", True),
         RegexLeaf("c", re.compile("c"), "c", False))}

    assert partial_lex("", lspec) == {()}
    assert partial_lex("d", lspec) == set()


def test_partial_lex_ignore():
    lspec = LexerSpec({
        RegexLeaf("a", re.compile("a")),
        RegexLeaf("b", re.compile("b")),
        RegexLeaf("c", re.compile("c"))
    }, re.compile("\\s+"))
    assert partial_lex("a b   c", lspec) == {
        (RegexLeaf("a", re.compile("a"), "a", True),
         RegexLeaf("b", re.compile("b"), "b", True),
         RegexLeaf("c", re.compile("c"), "c", False))}

    assert partial_lex("    ", lspec) == {()}


def test_partial_lex_disjoint():
    lspec = LexerSpec({
        RegexLeaf("a", re.compile("a+")),
        RegexLeaf("b", re.compile("b+")),
    }, re.compile(""))
    assert partial_lex("aaaa", lspec) == {
        (RegexLeaf("a", re.compile("a+"), "aaaa", False),)}

    assert partial_lex("aaabaabb", lspec) == {
        (RegexLeaf("a", re.compile("a+"), "aaa", True),
         RegexLeaf("b", re.compile("b+"), "b", True),
         RegexLeaf("a", re.compile("a+"), "aa", True),
         RegexLeaf("b", re.compile("b+"), "bb", False))}

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
        (RegexLeaf("print", re.compile(r'print\$'), "print$", True),
         RegexLeaf("lpar", re.compile("\\("), "(", True),
         RegexLeaf("var", re.compile("[a-z]+"), "foo", True),
         RegexLeaf("dot", re.compile("\\."), ".", True),
         RegexLeaf("caps", re.compile("tocaps"), "tocap", False)),
        (RegexLeaf("print", re.compile(r'print\$'), "print$", True),
         RegexLeaf("lpar", re.compile("\\("), "(", True),
         RegexLeaf("var", re.compile("[a-z]+"), "foo", True),
         RegexLeaf("dot", re.compile("\\."), ".", True),
         RegexLeaf("var", re.compile("[a-z]+"), "tocap", False))
    }

    assert partial_lex("  ))( zip prin", lspec) == {
        (RegexLeaf("rpar", re.compile("\\)"), ")", True),
         RegexLeaf("rpar", re.compile("\\)"), ")", True),
         RegexLeaf("lpar", re.compile("\\("), "(", True),
         RegexLeaf("var", re.compile("[a-z]+"), "zip", True),
         RegexLeaf("print", re.compile(r'print\$'), "prin", False)),
        (RegexLeaf("rpar", re.compile("\\)"), ")", True),
         RegexLeaf("rpar", re.compile("\\)"), ")", True),
         RegexLeaf("lpar", re.compile("\\("), "(", True),
         RegexLeaf("var", re.compile("[a-z]+"), "zip", True),
         RegexLeaf("var", re.compile("[a-z]+"), "prin", False))
    }

    assert partial_lex("  ))( zip prin ", lspec) == {
        (RegexLeaf("rpar", re.compile("\\)"), ")", True),
         RegexLeaf("rpar", re.compile("\\)"), ")", True),
         RegexLeaf("lpar", re.compile("\\("), "(", True),
         RegexLeaf("var", re.compile("[a-z]+"), "zip", True),
         RegexLeaf("var", re.compile("[a-z]+"), "prin", True))
    }


def test_partial_lex_finalize():
    lspec = LexerSpec({
        RegexLeaf("print", re.compile("print$")),
        RegexLeaf("var", re.compile("[a-z]+"))
    }, re.compile("\\s+"))
    assert partial_lex("a p", lspec) == {
        (RegexLeaf("var", re.compile("[a-z]+"), "a", True),
         RegexLeaf("var", re.compile("[a-z]+"), "p", False)),
        (RegexLeaf("var", re.compile("[a-z]+"), "a", True),
         RegexLeaf("print", re.compile("print$"), "p", False))
    }

    assert lex("a p", lspec) == {
        (RegexLeaf("var", re.compile("[a-z]+"), "a", True),
         RegexLeaf("var", re.compile("[a-z]+"), "p", True))
    }
