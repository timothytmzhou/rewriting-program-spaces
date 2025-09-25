from core.rewrite import rewrite
from core.grammar import TreeGrammar, Union, EmptySet, as_tree
from core.lexing.token import Token


@rewrite
def sum_of_evens(t: TreeGrammar) -> TreeGrammar:
    match t:
        case Union(children):
            return Union.of(sum_of_evens(c) for c in children)
        case Num(arg):
            token = as_tree(arg)
            match token:
                case Token(is_complete=True, prefix=prefix) if int(prefix) % 2 == 1:
                    return EmptySet()
                case _:
                    return t
        case Add(left, right):
            return Add(sum_of_evens(left), sum_of_evens(right))
        case _:
            return EmptySet()


# The demo expects a function named `pruner`.
pruner = sum_of_evens
