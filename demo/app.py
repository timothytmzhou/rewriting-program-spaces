import streamlit as st
from streamlit_ace import st_ace
from core.lark.from_lark import parse_attribute_grammar
from core.rewrite import rewriter
from core.grammar import Application
from importlib.resources import files
from llm.realizability import RealizabilityChecker

st.set_page_config(layout="wide")

# load initial code from files
pkg = "demo"
grammar_text = files(pkg).joinpath("grammar.lark").read_text()
ast_text     = files(pkg).joinpath("abstract_syntax.py").read_text()
rewrite_text = files(pkg).joinpath("pruner.py").read_text()

THEME = "monokai"

# two-column layout
col1, col2 = st.columns(2)
with col1:
    st.subheader("Lark Grammar")
    grammar_code: str = st_ace(
        value=grammar_text,
        language="python",
        height=200,
        key="grammar_editor",
        theme=THEME,
        auto_update=True,
    )
    st.subheader("Abstract Syntax")
    ast_code: str = st_ace(
        value=ast_text,
        language="python",
        height=300,
        key="ast_editor",
        theme=THEME,
        auto_update=True,
    )
with col2:
    st.subheader("Pruner")
    rewrite_code: str = st_ace(
        value=rewrite_text,
        language="python",
        height=500,
        key="rewrite_editor",
        theme=THEME,
        auto_update=True,
    )
    st.subheader("Input Prefix")
    prefix: str = st.text_input("Prefix:", key="prefix_input")
    button = st.button("Check Realizability", key="check_btn")

if button:
    rewriter.clear()
    ns: dict = {}
    try:
        exec(ast_code, ns)
        constructors = [
            constructor for constructor in ns.values()
            if isinstance(constructor, type) and issubclass(constructor, Application)
            and constructor.__module__ == "builtins"
        ]
        exec(rewrite_code, ns)
        rewrite_func = ns["pruner"]
        lexer_spec, parser = parse_attribute_grammar(
            constructors, grammar_code, "start"
        ).build_parser()

        checker = RealizabilityChecker(rewrite_func, parser, lexer_spec)
        result = checker.realizable(prefix)
        st.success(f"Realizable: {result}")
    except Exception as e:
        st.error(f"Error: {e}")
