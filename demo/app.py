import streamlit as st
from streamlit_ace import st_ace
from annotated_text import annotated_text
from core.lark.from_lark import parse_attribute_grammar
from core.rewrite import rewriter
from core.grammar import Application
from importlib.resources import files
from llm.realizability import RealizabilityChecker
from st_keyup import st_keyup


def find_maximal_valid_prefix(text: str, checker: RealizabilityChecker) -> int:
    for i in range(1, len(text) + 1):
        if not checker.realizable(text[:i]):
            return i - 1
    return len(text)

def update_validation():
    """Callback function to trigger rerun when input changes"""
    pass

st.set_page_config(layout="wide")

pkg = "demo"
grammar_text = files(pkg).joinpath("grammar.lark").read_text()
ast_text = files(pkg).joinpath("abstract_syntax.py").read_text()
rewrite_text = files(pkg).joinpath("pruner.py").read_text()

THEME = "xcode"

st.subheader("Input Prefix")
prefix = st_keyup("", key="prefix_input")

# Create placeholder for validation results
validation_container = st.container()

col1, col2 = st.columns(2)
with col1:
    st.subheader("Concrete Syntax")
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

# Update validation container with results
with validation_container:
    if prefix:
        try:
            rewriter.clear()
            ns: dict = {}
            exec(ast_code, ns)
            constructors = [
                constructor
                for constructor in ns.values()
                if isinstance(constructor, type)
                and issubclass(constructor, Application)
                and constructor.__module__ == "builtins"
            ]
            exec(rewrite_code, ns)
            rewrite_func = ns["pruner"]
            lexer_spec, parser = parse_attribute_grammar(
                constructors, grammar_code, "start"
            ).build_parser()

            checker = RealizabilityChecker(rewrite_func, parser, lexer_spec)
            max_valid_length = find_maximal_valid_prefix(prefix, checker)

            # Create annotated text
            valid_part = prefix[:max_valid_length]
            invalid_part = prefix[max_valid_length:]

            annotations = []
            if valid_part:
                annotations.append((valid_part, "", "#90EE90"))  # Light green
            if invalid_part:
                annotations.append((invalid_part, "", "#FFB6C1"))  # Light red

            annotated_text(*annotations)

        except Exception as e:
            st.error(f"Error: {e}")
