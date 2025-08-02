from core.rewrite import rewrite
from core.grammar import TreeGrammar, Union, EmptySet, as_tree
from core.lexing.token import Token


@rewrite
def even_sum(t: TreeGrammar) -> TreeGrammar:
    match t:
        case Union(children):
            return Union.of(even_sum(c) for c in children)
        case Num(arg):
            token = as_tree(arg)
            match token:
                case Token(is_complete=True, prefix=prefix) if int(prefix) % 2 == 1:
                    return EmptySet()
                case _:
                    return t
        case Add(left, right):
            return Union.of(
                Add(even_sum(left), even_sum(right)),
                Add(odd_sum(left), odd_sum(right)),
            )
        case _:
            return EmptySet()


@rewrite
def odd_sum(t: TreeGrammar) -> TreeGrammar:
    match t:
        case Union(children):
            return Union.of(odd_sum(c) for c in children)
        case Num(arg):
            token = as_tree(arg)
            match token:
                case Token(is_complete=True, prefix=prefix) if int(prefix) % 2 == 0:
                    return EmptySet()
                case _:
                    return t
        case Add(left, right):
            return Union.of(
                Add(odd_sum(left), even_sum(right)),
                Add(even_sum(left), odd_sum(right)),
            )
        case _:
            return EmptySet()


# The demo expects a function named `pruner`.
pruner = even_sum
