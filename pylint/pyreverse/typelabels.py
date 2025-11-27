"""Helpers to convert astroid annotations into UML friendly labels."""

from __future__ import annotations

from typing import Iterable, List

import astroid


_BUILTIN_TYPE_MAP = {
    "int": "Integer",
    "float": "Float",
    "str": "String",
    "bool": "Boolean",
    "bytes": "Bytes",
    "dict": "Dict",
    "list": "List",
    "set": "Set",
    "frozenset": "FrozenSet",
    "tuple": "Tuple",
    "type": "Type",
    "object": "Object",
}


def annotation_to_label(annotation: astroid.node_classes.NodeNG | None) -> str:
    """Return a normalized string representation for an annotation.

    The returned string is tailored for UML rendering: builtin names are mapped to
    their canonical title case representation and typing constructs are rendered
    using square brackets (``List[String]``).
    """

    if annotation is None or annotation is astroid.Uninferable:  # type: ignore[attr-defined]
        return ""

    if isinstance(annotation, astroid.Const):
        value = annotation.value
        if isinstance(value, str):
            return value
        if value is None:
            return "None"
        return str(value)

    if isinstance(annotation, astroid.Name):
        return _map_identifier(annotation.name)

    if isinstance(annotation, astroid.Attribute):
        return _map_identifier(_attribute_basename(annotation))

    if isinstance(annotation, astroid.Subscript):
        base = annotation_to_label(annotation.value)
        args = [annotation_to_label(arg) for arg in _subscript_arguments(annotation)]
        args = [arg for arg in args if arg]
        if not args:
            return base
        return f"{base}[{', '.join(args)}]"

    if isinstance(annotation, astroid.Tuple):
        return ", ".join(annotation_to_label(elt) for elt in annotation.elts)

    if isinstance(annotation, astroid.BinOp) and annotation.op == "|":
        flattened = _flatten_union(annotation)
        parts = [annotation_to_label(part) for part in flattened]
        return f"Union[{', '.join(parts)}]"

    return annotation.as_string()


def _map_identifier(identifier: str) -> str:
    base = identifier.split(".")[-1]
    return _BUILTIN_TYPE_MAP.get(base, base)


def _attribute_basename(node: astroid.Attribute) -> str:
    parts: List[str] = [node.attrname]
    expression = node.expr
    while isinstance(expression, astroid.Attribute):
        parts.append(expression.attrname)
        expression = expression.expr
    if isinstance(expression, astroid.Name):
        parts.append(expression.name)
    return parts[0]


def _subscript_arguments(node: astroid.Subscript) -> Iterable[astroid.NodeNG]:
    slice_node = node.slice
    if isinstance(slice_node, astroid.Tuple):
        return slice_node.elts
    if hasattr(astroid, "Index") and isinstance(slice_node, astroid.Index):  # type: ignore[attr-defined]
        return [slice_node.value]
    return [slice_node]


def _flatten_union(node: astroid.NodeNG) -> List[astroid.NodeNG]:
    if isinstance(node, astroid.BinOp) and node.op == "|":
        return _flatten_union(node.left) + _flatten_union(node.right)
    return [node]
