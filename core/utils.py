from collections.abc import Iterable

def flatten(args, container):
    if len(args) == 1 and isinstance(args[0], Iterable):
        return container(args[0])
    return container(args)
