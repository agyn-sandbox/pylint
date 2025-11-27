"""Tests for type hint rendering in pyreverse diagrams."""

import os
from types import SimpleNamespace

from pylint.pyreverse.diadefslib import DefaultDiadefGenerator, DiadefsHandler
from pylint.pyreverse.inspector import Linker, project_from_files
from pylint.pyreverse.writer import DotWriter

_DEFAULTS = {
    "all_ancestors": None,
    "show_associated": None,
    "module_names": None,
    "output_format": "dot",
    "diadefs_file": None,
    "quiet": 0,
    "show_ancestors": None,
    "classes": (),
    "all_associated": None,
    "mode": "PUB_ONLY",
    "show_builtin": False,
    "only_classnames": False,
    "output_directory": "",
}


class Config:
    def __init__(self):
        for attr, value in _DEFAULTS.items():
            setattr(self, attr, value)


def _build_class_diagram(module_name: str):
    module_path = os.path.join(os.path.dirname(__file__), "pyreverse_typing", module_name)
    project = project_from_files([module_path])
    linker = Linker(project)
    config = Config()
    handler = DiadefsHandler(config)
    diagrams = DefaultDiadefGenerator(linker, handler).visit(project)
    for diagram in diagrams:
        diagram.extract_relationships()
    class_diagram = next(diagram for diagram in diagrams if diagram.TYPE == "class")
    return class_diagram


def _get_entity(diagram, class_name: str):
    return next(entity for entity in diagram.objects if entity.node.name == class_name)


def test_method_signatures_show_type_hints():
    diagram = _build_class_diagram("pyreverse_typing.py")
    user_entity = _get_entity(diagram, "User")

    writer = DotWriter(SimpleNamespace(output_format="dot", only_classnames=False))
    values = writer.get_values(user_entity)
    label = values["label"]

    assert "add_tag(tag: String) -> List[String]" in label
    assert "from_payload(payload: Dict[String, String]) -> User" in label
    assert "self" not in label


def test_attribute_labels_include_annotations():
    diagram = _build_class_diagram("pyreverse_typing.py")
    user_entity = _get_entity(diagram, "User")

    expected = {
        "alias : Optional[String]",
        "identifier : Integer",
        "metadata : Dict[String, Integer]",
        "owner : Union[Team, None]",
        "tags : List[String]",
        "username : String",
    }

    assert expected.issubset(set(user_entity.attrs))
