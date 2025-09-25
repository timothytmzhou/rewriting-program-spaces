import streamlit as st
from streamlit_ace import st_ace
from annotated_text import annotated_text
from core.lark.from_lark import parse_attribute_grammar
from core.rewrite import rewriter
from core.grammar import Application
from importlib.resources import files
from demo.filter_sort.filter_sort import constructors
from llm.realizability import RealizabilityChecker
from st_keyup import st_keyup
from experiments.egraph.egraph import egraph_from_egglog, in_egraph


# Constants
THEME = "xcode"
PRESET_OPTIONS = [
    "Choose preset...",
    "sort (filter pred l)",
    "filter pred (sort l)",
    "filter pred l",
    "sort l",
    "sort (",
    "otherFunction",
]


# Resource loading
@st.cache_resource
def _get_rewriter_lock():
    import threading

    return threading.RLock()


def build_list_checker() -> RealizabilityChecker:
    fs_dir = files("demo").joinpath("filter_sort")
    lark_source = fs_dir.joinpath("filter_sort.lark").read_text()
    lexer_spec, grammar = parse_attribute_grammar(
        constructors, lark_source, "start"
    ).build_parser()
    egglog_source = fs_dir.joinpath("filter_sort.egglog").read_text()
    egraph = egraph_from_egglog(egglog_source, "start", "Expr")
    return RealizabilityChecker(in_egraph(egraph), grammar, lexer_spec)


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


def find_maximal_valid_prefix(text: str, checker: RealizabilityChecker) -> int:
    with _realizability_lock:
        rewriter.clear()
        for i in range(1, len(text) + 1):
            if not checker.realizable(text[:i]):
                return i - 1
        return len(text)


# Initialize resources
_realizability_lock = _get_rewriter_lock()
pkg = "demo"
grammar_text = files(pkg).joinpath("grammar.lark").read_text()
ast_text = files(pkg).joinpath("abstract_syntax.py").read_text()
rewrite_text = files(pkg).joinpath("pruner.py").read_text()

# Page configuration
st.set_page_config(layout="wide")

# UI containers
prefix_container = st.container()
validation_container = st.container()

# Main configuration
checker_type = st.selectbox("Checker Type", ["custom", "e-graph"], index=1)
checker: RealizabilityChecker | None = None

# Input prefix section
with prefix_container:
    left, right = st.columns([2, 1])
    with left:
        st.subheader("Input Prefix")
        # Include the selected preset in the key to force re-evaluation
        selected_preset = st.session_state.get("prefix_preset_select", "Choose preset...")
        st_keyup(
            "",
            key=f"prefix_input_{hash(selected_preset)}",
            debounce=500,
            value=st.session_state.get("prefix_input", "sort (filter pred (sort l))"),
        )
        # Sync the actual prefix_input with the current keyup value
        current_key = f"prefix_input_{hash(selected_preset)}"
        if current_key in st.session_state:
            st.session_state["prefix_input"] = st.session_state[current_key]
    with right:
        if checker_type == "e-graph":

            def _apply_preset():
                sel = st.session_state.get("prefix_preset_select")
                if sel and sel != "Choose preset...":
                    st.session_state["prefix_input"] = sel

            st.subheader("Presets")
            st.selectbox(
                "Prefix presets",
                options=PRESET_OPTIONS,
                index=0,
                key="prefix_preset_select",
                on_change=_apply_preset,
            )

# Checker-specific UI and setup
if checker_type == "custom":
    # Custom checker: code editors
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

    # Build custom checker
    try:
        with _realizability_lock:
            checker = build_custom_checker(grammar_code, ast_code, rewrite_code)
    except Exception as e:
        st.error(f"Failed to build custom checker: {e}")
        checker = None
else:
    # E-graph checker: description and setup
    st.markdown(
        """
        <div style="padding:1.5rem;border:1px solid #ddd;border-radius:12px;background:linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);">
          <h4 style="margin:0 0 1rem 0;color:#495057;font-weight:normal;">Refactor this program to something equivalent:</h4>
          <div style="text-align:left;margin:1rem 0;">
            <pre style="display:inline-block;background:#1a1a1a;color:#f8f8f2;padding:1rem;border-radius:8px;font-size:1.1em;"><code>sort (filter pred (sort l))</code></pre>
          </div>
          Rewrite rules:
          <div style="background:#fff;padding:1rem;border-radius:6px;border-left:4px solid #007bff;">
            <div style="margin:0.5rem 0;font-family:monospace;"><code>sort (sort l) => sort l</code></div>
            <div style="margin:0.5rem 0;font-family:monospace;"><code>filter pred (filter pred l) => filter pred l</code></div>
            <div style="margin:0.5rem 0;font-family:monospace;"><code>sort (filter pred l) <=> filter pred (sort l)</code></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    if "egraph_checker" not in st.session_state:
        with _realizability_lock:
            st.session_state["egraph_checker"] = build_list_checker()
    checker = st.session_state.get("egraph_checker")

# Validation and results
with validation_container:
    if checker is not None:
        max_valid_length = find_maximal_valid_prefix(
            st.session_state["prefix_input"], checker
        )
        valid_part = st.session_state["prefix_input"][:max_valid_length]
        invalid_part = st.session_state["prefix_input"][max_valid_length:]
        annotations = []
        if valid_part:
            annotations.append((valid_part, "", "#90EE90"))
        if invalid_part:
            annotations.append((invalid_part, "", "#FFB6C1"))
        annotated_text(*annotations)
