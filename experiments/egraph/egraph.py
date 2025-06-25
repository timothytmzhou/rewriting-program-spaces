import json
from typing import Callable
from functools import partial
from collections import defaultdict
from egglog.bindings import EGraph
from core.grammar import *
from core.rewrite import rewrite
from lexing.leaves import Token

START_RELATION = "__start__"  # dummy relation for the start symbol


@dataclass(frozen=True)
class ENode:
    op: str
    children: tuple[str]  # list of names of children eclasses


EClassMapping = dict[str, set[ENode]]  # maps eclass names to contained enodes


def root_and_eclass_mapping(egraph: EGraph) -> tuple[str, EClassMapping]:
    """
    Extracts the root eclass and a mapping of eclasses to their contained ENodes.
    """
    # Hack to work around egglog python not providing a way to iterate over eclasses.
    egraph_json = json.loads(egraph.serialize([]).to_json())
    nodes = egraph_json["nodes"]
    root_eclass = None
    eclasses = defaultdict(set)

    for node_data in nodes.values():
        eclass, op = node_data["eclass"], node_data["op"]
        if op.startswith('"') and op.endswith('"'):
            op = op[1:-1]  # TODO: this is a hack to unescape variable names
        children_eclasses = tuple(nodes[enode]["eclass"]
                                  for enode in node_data["children"])
        if op == START_RELATION:
            root_eclass = children_eclasses[0]
        else:
            eclasses[eclass].add(ENode(op, children_eclasses))
    assert root_eclass is not None, "No start relation found in the egraph."
    return root_eclass, eclasses


def in_egraph(egraph: EGraph) -> Callable[[TreeGrammar], TreeGrammar]:
    """
    Given an egraph, returns a predicate on TreeGrammars that computes the intersection
    of the grammar with the egraph.
    """
    root_eclass, eclasses = root_and_eclass_mapping(egraph)

    @rewrite
    def in_eclass(eclass: str, t: TreeGrammar) -> TreeGrammar:
        match t:
            case EmptySet():
                return EmptySet()
            case Union(children):
                return Union.of(in_eclass(eclass, child) for child in children)
            case Constant(Token(prefix=prefix, is_complete=True)):
                matches_constant = any(enode.op == prefix and not enode.children
                                       for enode in eclasses[eclass])
                return t if matches_constant else EmptySet()
            case Constant(Token(prefix=prefix, token_regex=token_regex, is_complete=False)):
                matches_constant = any(
                    not enode.children and
                    enode.op.startswith(prefix) and
                    token_regex.fullmatch(enode.op, partial=True)
                    for enode in eclasses[eclass]
                )
                return t if matches_constant else EmptySet()
            case Application(f, children):
                matches = []
                for enode in eclasses[eclass]:
                    if f == enode.op:
                        assert len(enode.children) == len(children)
                        matches.append(Application.of(
                            enode.op,
                            [in_eclass(child_eclass, child)
                             for child_eclass, child in zip(enode.children, children)]
                        ))
                return Union.of(matches)
            case _:
                raise ValueError

    return partial(in_eclass, root_eclass)


def egraph_from_egglog(egglog_source: str, start: str, start_type: str) -> EGraph:
    egglog_source += f"\n(relation {START_RELATION} ({start_type}))"
    egglog_source += f"\n({START_RELATION} {start})"
    egraph = EGraph()
    commands = egraph.parse_program(egglog_source)
    egraph.run_program(*commands)
    return egraph

# equiv(e_graph):
# do constrained decoding until let x = expr1 is generated
# then recurse on equiv(e_graph[x=>expr1])
