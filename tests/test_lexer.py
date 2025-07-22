from lexing.lexing import *
from lexing.token import Token
import regex as re


def test_partial_lex_abc():
    lspec = LexerSpec(frozenset({
        Token("a", re.compile("a")),
        Token("b", re.compile("b")),
        Token("c", re.compile("c"))
    }), re.compile(""))
    assert partial_lex("abc", lspec) == {
        (Token("a", re.compile("a"), "a", True),
         Token("b", re.compile("b"), "b", True),
         Token("c", re.compile("c"), "c", False))}

    assert partial_lex("", lspec) == {()}
    assert partial_lex("d", lspec) == set()


def test_partial_lex_ignore():
    lspec = LexerSpec(frozenset({
        Token("a", re.compile("a")),
        Token("b", re.compile("b")),
        Token("c", re.compile("c"))
    }), re.compile("\\s+"))
    assert partial_lex("a b   c", lspec) == {
        (Token("a", re.compile("a"), "a", True),
         Token("b", re.compile("b"), "b", True),
         Token("c", re.compile("c"), "c", False))}

    assert partial_lex("    ", lspec) == {()}


def test_partial_lex_disjoint():
    lspec = LexerSpec(frozenset({
        Token("a", re.compile("a+")),
        Token("b", re.compile("b+")),
    }), re.compile(""))
    assert partial_lex("aaaa", lspec) == {
        (Token("a", re.compile("a+"), "aaaa", False),)}

    assert partial_lex("aaabaabb", lspec) == {
        (Token("a", re.compile("a+"), "aaa", True),
         Token("b", re.compile("b+"), "b", True),
         Token("a", re.compile("a+"), "aa", True),
         Token("b", re.compile("b+"), "bb", False))}

    assert partial_lex("", lspec) == {()}


def test_partial_lex_nonsingleton():
    lspec = LexerSpec(frozenset({
        Token("print", re.compile(r'print\$')),
        Token("lpar", re.compile("\\(")),
        Token("rpar", re.compile("\\)")),
        Token("var", re.compile("[a-z]+")),
        Token("dot", re.compile("\\.")),
        Token("caps", re.compile("tocaps"))
    }), re.compile("\\s+"))
    assert partial_lex("print$( foo.tocap", lspec) == {
        (Token("print", re.compile(r'print\$'), "print$", True),
         Token("lpar", re.compile("\\("), "(", True),
         Token("var", re.compile("[a-z]+"), "foo", True),
         Token("dot", re.compile("\\."), ".", True),
         Token("caps", re.compile("tocaps"), "tocap", False)),
        (Token("print", re.compile(r'print\$'), "print$", True),
         Token("lpar", re.compile("\\("), "(", True),
         Token("var", re.compile("[a-z]+"), "foo", True),
         Token("dot", re.compile("\\."), ".", True),
         Token("var", re.compile("[a-z]+"), "tocap", False))
    }

    assert partial_lex("  ))( zip prin", lspec) == {
        (Token("rpar", re.compile("\\)"), ")", True),
         Token("rpar", re.compile("\\)"), ")", True),
         Token("lpar", re.compile("\\("), "(", True),
         Token("var", re.compile("[a-z]+"), "zip", True),
         Token("print", re.compile(r'print\$'), "prin", False)),
        (Token("rpar", re.compile("\\)"), ")", True),
         Token("rpar", re.compile("\\)"), ")", True),
         Token("lpar", re.compile("\\("), "(", True),
         Token("var", re.compile("[a-z]+"), "zip", True),
         Token("var", re.compile("[a-z]+"), "prin", False))
    }

    assert partial_lex("  ))( zip prin ", lspec) == {
        (Token("rpar", re.compile("\\)"), ")", True),
         Token("rpar", re.compile("\\)"), ")", True),
         Token("lpar", re.compile("\\("), "(", True),
         Token("var", re.compile("[a-z]+"), "zip", True),
         Token("var", re.compile("[a-z]+"), "prin", True))
    }


def test_partial_lex_finalize():
    lspec = LexerSpec(frozenset({
        Token("print", re.compile("print$")),
        Token("var", re.compile("[a-z]+"))
    }), re.compile("\\s+"))
    assert partial_lex("a p", lspec) == {
        (Token("var", re.compile("[a-z]+"), "a", True),
         Token("var", re.compile("[a-z]+"), "p", False)),
        (Token("var", re.compile("[a-z]+"), "a", True),
         Token("print", re.compile("print$"), "p", False))
    }

    assert lex("a p", lspec) == {
        (Token("var", re.compile("[a-z]+"), "a", True),
         Token("var", re.compile("[a-z]+"), "p", True))
    }
