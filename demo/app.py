import streamlit as st
from streamlit_ace import st_ace
from annotated_text import annotated_text
from core.lark.from_lark import parse_attribute_grammar
from core.rewrite import rewriter
from core.grammar import Application
from importlib.resources import files
from llm.realizability import RealizabilityChecker
from st_keyup import st_keyup
from experiments.egraph.scripts.run import build_checker, load_benchmark
import threading


_realizability_lock = threading.RLock()


def find_maximal_valid_prefix(text: str, checker: RealizabilityChecker) -> int:
    with _realizability_lock:
        rewriter.clear()
        for i in range(1, len(text) + 1):
            if not checker.realizable(text[:i]):
                return i - 1
        return len(text)


st.set_page_config(layout="wide")

pkg = "demo"
grammar_text = files(pkg).joinpath("grammar.lark").read_text()
ast_text = files(pkg).joinpath("abstract_syntax.py").read_text()
rewrite_text = files(pkg).joinpath("pruner.py").read_text()

THEME = "xcode"

st.subheader("Input Prefix")
prefix = st_keyup("", key="prefix_input", debounce=500, value="hi")

validation_container = st.container()

checker_type = st.selectbox("Checker Type", ["custom", "e-graph"], index=1)

# Prepare holder for the selected checker
checker: RealizabilityChecker | None = None


def build_custom_checker(
    grammar_code: str, ast_code: str, rewrite_code: str
) -> RealizabilityChecker:
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
    return RealizabilityChecker(rewrite_func, parser, lexer_spec)


if checker_type == "custom":
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Concrete Syntax")
        grammar_code = st_ace(
            value=grammar_text,
            language="python",
            height=200,
            key="grammar_editor",
            theme=THEME,
            auto_update=True,
        )
        st.subheader("Abstract Syntax")
        ast_code = st_ace(
            value=ast_text,
            language="python",
            height=300,
            key="ast_editor",
            theme=THEME,
            auto_update=True,
        )
    with col2:
        st.subheader("Pruner")
        rewrite_code = st_ace(
            value=rewrite_text,
            language="python",
            height=500,
            key="rewrite_editor",
            theme=THEME,
            auto_update=True,
        )
    # Build checker from the edited sources
    try:
        with _realizability_lock:
            checker = build_custom_checker(grammar_code, ast_code, rewrite_code)
    except Exception as e:
        st.error(f"Failed to build custom checker: {e}")
        checker = None
else:
    st.subheader("E-Graph Source (Egglog)")
    _, egraph_source = load_benchmark("lerp.egglog")
    if "egraph_checker" not in st.session_state:
        try:
            with _realizability_lock:
                st.session_state["egraph_checker"] = build_checker(egraph_source)
        except Exception as e:
            st.error(f"Failed to build e-graph checker: {e}")
    checker = st.session_state.get("egraph_checker")

# Unified validation and rendering
with validation_container:
    if not prefix:
        st.info("Type in the input prefix to validate.")
    else:
        if checker is not None:
            max_valid_length = find_maximal_valid_prefix(prefix, checker)
            valid_part = prefix[:max_valid_length]
            invalid_part = prefix[max_valid_length:]
            annotations = []
            if valid_part:
                annotations.append((valid_part, "", "#90EE90"))
            if invalid_part:
                annotations.append((invalid_part, "", "#FFB6C1"))
            annotated_text(*annotations)
