# Copyright (c) 2015-2020 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2017 Łukasz Rogalski <rogalski.91@gmail.com>
# Copyright (c) 2018 ssolanki <sushobhitsolanki@gmail.com>
# Copyright (c) 2018 Ville Skyttä <ville.skytta@iki.fi>
# Copyright (c) 2019-2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>
# Copyright (c) 2019 Hugo van Kemenade <hugovk@users.noreply.github.com>
# Copyright (c) 2020 hippo91 <guillaume.peillex@gmail.com>
# Copyright (c) 2020 Anthony Sottile <asottile@umich.edu>

# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/PyCQA/pylint/blob/master/LICENSE

"""
Visitor doing some postprocessing on the astroid tree.
Try to resolve definitions (namespace) dictionary, relationship...
"""
import ast
import collections
import os
import traceback

import astroid

from pylint.pyreverse import utils


def _iface_hdlr(_):
    """Handler used by interfaces to handle suspicious interface nodes."""
    return True


def _astroid_wrapper(func, modname):
    print("parsing %s..." % modname)
    try:
        return func(modname)
    except astroid.exceptions.AstroidBuildingException as exc:
        print(exc)
    except Exception:  # pylint: disable=broad-except
        traceback.print_exc()
    return None


def interfaces(node, herited=True, handler_func=_iface_hdlr):
    """Return an iterator on interfaces implemented by the given class node."""
    try:
        implements = astroid.bases.Instance(node).getattr("__implements__")[0]
    except astroid.exceptions.NotFoundError:
        return
    if not herited and implements.frame() is not node:
        return
    found = set()
    missing = False
    for iface in astroid.node_classes.unpack_infer(implements):
        if iface is astroid.Uninferable:
            missing = True
            continue
        if iface not in found and handler_func(iface):
            found.add(iface)
            yield iface
    if missing:
        raise astroid.exceptions.InferenceError()


class IdGeneratorMixIn:
    """Mixin adding the ability to generate integer uid."""

    def __init__(self, start_value=0):
        self.id_count = start_value

    def init_counter(self, start_value=0):
        """init the id counter"""
        self.id_count = start_value

    def generate_id(self):
        """generate a new identifier"""
        self.id_count += 1
        return self.id_count


class Linker(IdGeneratorMixIn, utils.LocalsVisitor):
    """Walk on the project tree and resolve relationships.

    According to options the following attributes may be
    added to visited nodes:

    * uid,
      a unique identifier for the node (on astroid.Project, astroid.Module,
      astroid.Class and astroid.locals_type). Only if the linker
      has been instantiated with tag=True parameter (False by default).

    * Function
      a mapping from locals names to their bounded value, which may be a
      constant like a string or an integer, or an astroid node
      (on astroid.Module, astroid.Class and astroid.Function).

    * instance_attrs_type
      as locals_type but for klass member attributes (only on astroid.Class)

    * implements,
      list of implemented interface _objects_ (only on astroid.Class nodes)
    """

    _OPTIONAL_NAMES = {"Optional", "typing.Optional"}
    _UNION_NAMES = {"Union", "typing.Union"}
    _LIST_NAMES = {"List", "typing.List", "list"}
    _SET_NAMES = {"Set", "typing.Set", "set"}
    _DICT_NAMES = {"Dict", "typing.Dict", "dict"}
    _TUPLE_NAMES = {"Tuple", "typing.Tuple", "tuple"}
    _ANNOTATED_NAMES = {"Annotated", "typing.Annotated"}
    _LITERAL_NAMES = {"Literal", "typing.Literal"}

    def __init__(self, project, inherited_interfaces=0, tag=False):
        IdGeneratorMixIn.__init__(self)
        utils.LocalsVisitor.__init__(self)
        # take inherited interface in consideration or not
        self.inherited_interfaces = inherited_interfaces
        # tag nodes or not
        self.tag = tag
        # visited project
        self.project = project

    def visit_project(self, node):
        """visit a pyreverse.utils.Project node

        * optionally tag the node with a unique id
        """
        if self.tag:
            node.uid = self.generate_id()
        for module in node.modules:
            self.visit(module)

    def visit_package(self, node):
        """visit an astroid.Package node

        * optionally tag the node with a unique id
        """
        if self.tag:
            node.uid = self.generate_id()
        for subelmt in node.values():
            self.visit(subelmt)

    def visit_module(self, node):
        """visit an astroid.Module node

        * set the locals_type mapping
        * set the depends mapping
        * optionally tag the node with a unique id
        """
        if hasattr(node, "locals_type"):
            return
        node.locals_type = collections.defaultdict(list)
        node.depends = []
        if self.tag:
            node.uid = self.generate_id()

    def visit_classdef(self, node):
        """visit an astroid.Class node

        * set the locals_type and instance_attrs_type mappings
        * set the implements list and build it
        * optionally tag the node with a unique id
        """
        if hasattr(node, "locals_type"):
            return
        node.locals_type = collections.defaultdict(list)
        if self.tag:
            node.uid = self.generate_id()
        # resolve ancestors
        for baseobj in node.ancestors(recurs=False):
            specializations = getattr(baseobj, "specializations", [])
            specializations.append(node)
            baseobj.specializations = specializations
        # resolve instance attributes
        node.instance_attrs_type = collections.defaultdict(list)
        for assignattrs in node.instance_attrs.values():
            for assignattr in assignattrs:
                if not isinstance(assignattr, astroid.Unknown):
                    self.handle_assignattr_type(assignattr, node)
        node.inferred_annotations = {}
        self._collect_annotations(node)
        # resolve implemented interface
        try:
            node.implements = list(interfaces(node, self.inherited_interfaces))
        except astroid.InferenceError:
            node.implements = ()

    def visit_functiondef(self, node):
        """visit an astroid.Function node

        * set the locals_type mapping
        * optionally tag the node with a unique id
        """
        if hasattr(node, "locals_type"):
            return
        node.locals_type = collections.defaultdict(list)
        if self.tag:
            node.uid = self.generate_id()

    link_project = visit_project
    link_module = visit_module
    link_class = visit_classdef
    link_function = visit_functiondef

    def visit_assignname(self, node):
        """visit an astroid.AssignName node

        handle locals_type
        """
        # avoid double parsing done by different Linkers.visit
        # running over the same project:
        if hasattr(node, "_handled"):
            return
        node._handled = True
        if node.name in node.frame():
            frame = node.frame()
        else:
            # the name has been defined as 'global' in the frame and belongs
            # there.
            frame = node.root()
        try:
            if not hasattr(frame, "locals_type"):
                # If the frame doesn't have a locals_type yet,
                # it means it wasn't yet visited. Visit it now
                # to add what's missing from it.
                if isinstance(frame, astroid.ClassDef):
                    self.visit_classdef(frame)
                elif isinstance(frame, astroid.FunctionDef):
                    self.visit_functiondef(frame)
                else:
                    self.visit_module(frame)

            current = frame.locals_type[node.name]
            values = set(node.infer())
            frame.locals_type[node.name] = list(set(current) | values)
        except astroid.InferenceError:
            pass

    @staticmethod
    def handle_assignattr_type(node, parent):
        """handle an astroid.assignattr node

        handle instance_attrs_type
        """
        try:
            values = set(node.infer())
            current = set(parent.instance_attrs_type[node.attrname])
            parent.instance_attrs_type[node.attrname] = list(current | values)
        except astroid.InferenceError:
            pass

    def _collect_annotations(self, class_node):
        if not hasattr(class_node, "body"):
            return
        for stmt in class_node.body:
            if isinstance(stmt, astroid.AnnAssign) and isinstance(
                stmt.target, astroid.AssignName
            ):
                attr_name = stmt.target.name
                typestr, targets = self._resolve_annotation_to_typestr(
                    stmt.annotation, class_node
                )
                if typestr:
                    class_node.inferred_annotations[attr_name] = typestr
                self._extend_type_mapping(class_node.locals_type, attr_name, targets)
        for method in getattr(class_node, "mymethods", lambda: [])():
            if method.type != "method":
                continue
            self_names = self._get_self_names(method)
            if not self_names:
                continue
            param_annotations = self._extract_param_annotations(method)
            for stmt in method.body:
                if (
                    isinstance(stmt, astroid.AnnAssign)
                    and isinstance(stmt.target, astroid.AssignAttr)
                    and self._is_self_attribute(stmt.target, self_names)
                ):
                    attr_name = stmt.target.attrname
                    typestr, targets = self._resolve_annotation_to_typestr(
                        stmt.annotation, method
                    )
                    if typestr:
                        class_node.inferred_annotations[attr_name] = typestr
                    self._extend_type_mapping(
                        class_node.instance_attrs_type, attr_name, targets
                    )
                elif isinstance(stmt, astroid.Assign):
                    for target in stmt.targets:
                        if not (
                            isinstance(target, astroid.AssignAttr)
                            and self._is_self_attribute(target, self_names)
                            and isinstance(stmt.value, astroid.Name)
                        ):
                            continue
                        attr_name = target.attrname
                        annotation = param_annotations.get(stmt.value.name)
                        if not annotation:
                            continue
                        typestr, targets = annotation
                        if typestr and attr_name not in class_node.inferred_annotations:
                            class_node.inferred_annotations[attr_name] = typestr
                        self._extend_type_mapping(
                            class_node.instance_attrs_type, attr_name, targets
                        )

    @staticmethod
    def _extend_type_mapping(mapping, name, nodes):
        if not nodes:
            return
        current = mapping[name]
        for node in nodes:
            if node not in current:
                current.append(node)

    def _extract_param_annotations(self, method):
        annotations = {}

        def register(arg_node, annotation_node):
            if annotation_node is None:
                return
            typestr, targets = self._resolve_annotation_to_typestr(
                annotation_node, method
            )
            if typestr or targets:
                annotations[arg_node.name] = (typestr, targets)

        args = method.args
        posonlyargs = getattr(args, "posonlyargs", [])
        posonly_annotations = getattr(args, "posonlyargs_annotations", [])
        for arg, ann in zip(posonlyargs, posonly_annotations):
            register(arg, ann)
        positional_annotations = list(args.annotations)
        for arg, ann in zip(args.args, positional_annotations):
            register(arg, ann)
        if args.vararg and args.varargannotation:
            register(args.vararg, args.varargannotation)
        kwonly_annotations = list(args.kwonlyargs_annotations)
        for arg, ann in zip(args.kwonlyargs, kwonly_annotations):
            register(arg, ann)
        if args.kwarg and args.kwargannotation:
            register(args.kwarg, args.kwargannotation)
        return annotations

    def _resolve_annotation_to_typestr(self, annotation, context):
        if annotation is None:
            return "", set()
        if isinstance(annotation, astroid.Const) and isinstance(annotation.value, str):
            source = annotation.value
        else:
            try:
                source = annotation.as_string()
            except AttributeError:
                return "", set()
        source = source.strip()
        if not source:
            return "", set()
        try:
            expr = ast.parse(source, mode="eval").body
        except SyntaxError:
            normalized = source.replace("typing.", "")
            return normalized, set()
        normalized, referenced = self._normalize_annotation_expression(expr)
        targets = self._lookup_class_targets(referenced, context)
        return normalized, targets

    def _normalize_annotation_expression(self, node, parent=None, grandparent=None):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            parts = []
            refs = set()
            for child in self._flatten_union(node):
                text, child_refs = self._normalize_annotation_expression(
                    child, parent, grandparent
                )
                parts.append(text)
                refs |= child_refs
            return " | ".join(self._dedupe_ordered(parts)), refs
        if isinstance(node, ast.Subscript):
            base_name = self._qualified_name(node.value)
            args = list(self._iter_subscript_args(node.slice))
            if base_name in self._OPTIONAL_NAMES:
                parts = []
                refs = set()
                for arg in args:
                    text, child_refs = self._normalize_annotation_expression(
                        arg, node, parent
                    )
                    parts.append(text)
                    refs |= child_refs
                parts.append("None")
                return " | ".join(self._dedupe_ordered(parts)), refs
            if base_name in self._UNION_NAMES:
                parts = []
                refs = set()
                for arg in args:
                    text, child_refs = self._normalize_annotation_expression(
                        arg, node, parent
                    )
                    parts.append(text)
                    refs |= child_refs
                return " | ".join(self._dedupe_ordered(parts)), refs
            if base_name in self._ANNOTATED_NAMES:
                if args:
                    return self._normalize_annotation_expression(args[0], node, parent)
                return "Annotated", set()
            if base_name in self._LIST_NAMES:
                inner, refs = (
                    self._normalize_annotation_expression(args[0], node, parent)
                    if args
                    else ("Any", set())
                )
                return f"list[{inner}]", refs
            if base_name in self._SET_NAMES:
                inner, refs = (
                    self._normalize_annotation_expression(args[0], node, parent)
                    if args
                    else ("Any", set())
                )
                return f"set[{inner}]", refs
            if base_name in self._DICT_NAMES:
                if len(args) >= 2:
                    key_text, key_refs = self._normalize_annotation_expression(
                        args[0], node, parent
                    )
                    value_text, value_refs = self._normalize_annotation_expression(
                        args[1], node, parent
                    )
                    refs = key_refs | value_refs
                    return f"dict[{key_text}, {value_text}]", refs
                if args:
                    inner, refs = self._normalize_annotation_expression(
                        args[0], node, parent
                    )
                    return f"dict[{inner}]", refs
            if base_name in self._TUPLE_NAMES:
                parts = []
                refs = set()
                for arg in args:
                    text, child_refs = self._normalize_annotation_expression(
                        arg, node, parent
                    )
                    parts.append(text)
                    refs |= child_refs
                return f"tuple[{', '.join(parts)}]", refs
            base_text, base_refs = self._normalize_annotation_expression(
                node.value, node, parent
            )
            arg_texts = []
            refs = set(base_refs)
            for arg in args:
                text, child_refs = self._normalize_annotation_expression(
                    arg, node, parent
                )
                arg_texts.append(text)
                refs |= child_refs
            return f"{base_text}[{', '.join(arg_texts)}]", refs
        if isinstance(node, ast.Attribute):
            base_text, base_refs = self._normalize_annotation_expression(
                node.value, node, parent
            )
            if base_text:
                full = f"{base_text}.{node.attr}"
            else:
                full = node.attr
            base_refs.add(full)
            return full, base_refs
        if isinstance(node, ast.Name):
            return node.id, {node.id}
        if isinstance(node, ast.Constant):
            if node.value is None:
                return "None", set()
            if isinstance(node.value, str):
                if (
                    isinstance(parent, ast.Subscript)
                    and self._qualified_name(parent.value) in self._LITERAL_NAMES
                ) or (
                    isinstance(parent, ast.Tuple)
                    and isinstance(grandparent, ast.Subscript)
                    and self._qualified_name(grandparent.value) in self._LITERAL_NAMES
                ):
                    return repr(node.value), set()
                text = node.value.strip()
                if self._is_valid_identifier(text) or self._is_dotted_identifier(text):
                    return text, {text}
                return repr(node.value), set()
            return repr(node.value), set()
        if isinstance(node, ast.Tuple):
            parts = []
            refs = set()
            for arg in node.elts:
                text, child_refs = self._normalize_annotation_expression(
                    arg, node, parent
                )
                parts.append(text)
                refs |= child_refs
            return ", ".join(parts), refs
        if isinstance(node, ast.List):
            parts = []
            refs = set()
            for arg in node.elts:
                text, child_refs = self._normalize_annotation_expression(
                    arg, node, parent
                )
                parts.append(text)
                refs |= child_refs
            return ", ".join(parts), refs
        if isinstance(node, ast.Ellipsis):
            return "...", set()
        try:
            text = ast.unparse(node)
        except AttributeError:
            text = source = ""
        else:
            source = text
        return source, set()

    @staticmethod
    def _flatten_union(node):
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            yield from Linker._flatten_union(node.left)
            yield from Linker._flatten_union(node.right)
        else:
            yield node

    @staticmethod
    def _iter_subscript_args(slice_node):
        if isinstance(slice_node, ast.Tuple):
            return list(slice_node.elts)
        if isinstance(slice_node, ast.List):
            return list(slice_node.elts)
        if hasattr(ast, "Index") and isinstance(
            slice_node, ast.Index
        ):  # pragma: no cover
            return Linker._iter_subscript_args(slice_node.value)
        return [slice_node]

    @staticmethod
    def _qualified_name(node):
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            left = Linker._qualified_name(node.value)
            return f"{left}.{node.attr}" if left else node.attr
        return None

    @staticmethod
    def _dedupe_ordered(items):
        result = []
        seen = set()
        for item in items:
            if item not in seen:
                seen.add(item)
                result.append(item)
        return result

    @staticmethod
    def _is_valid_identifier(value):
        return value.isidentifier()

    @staticmethod
    def _is_dotted_identifier(value):
        parts = value.split(".")
        return all(part.isidentifier() for part in parts)

    def _lookup_class_targets(self, names, context):
        targets = set()
        for name in names:
            for node in self._lookup_nodes(name, context):
                if isinstance(node, astroid.ClassDef) and self._is_project_class(node):
                    targets.add(node)
        return targets

    def _lookup_nodes(self, name, context):
        parts = name.split(".")
        try:
            _, nodes = context.lookup(parts[0])
        except astroid.exceptions.NotFoundError:
            return []
        current = list(nodes)
        for part in parts[1:]:
            next_nodes = []
            for node in current:
                try:
                    next_nodes.extend(node.igetattr(part))
                except (astroid.exceptions.NotFoundError, astroid.InferenceError):
                    continue
            if not next_nodes:
                return []
            current = next_nodes
        return current

    def _is_project_class(self, class_node):
        module = class_node.root()
        return isinstance(module, astroid.Module) and module.name in getattr(
            self.project, "locals", {}
        )

    @staticmethod
    def _is_self_attribute(target, self_names):
        return (
            isinstance(target, astroid.AssignAttr)
            and isinstance(target.expr, astroid.Name)
            and target.expr.name in self_names
        )

    @staticmethod
    def _get_self_names(method):
        args = method.args
        if getattr(args, "posonlyargs", None):
            return {args.posonlyargs[0].name}
        if args.args:
            return {args.args[0].name}
        return set()

    def visit_import(self, node):
        """visit an astroid.Import node

        resolve module dependencies
        """
        context_file = node.root().file
        for name in node.names:
            relative = astroid.modutils.is_relative(name[0], context_file)
            self._imported_module(node, name[0], relative)

    def visit_importfrom(self, node):
        """visit an astroid.ImportFrom node

        resolve module dependencies
        """
        basename = node.modname
        context_file = node.root().file
        if context_file is not None:
            relative = astroid.modutils.is_relative(basename, context_file)
        else:
            relative = False
        for name in node.names:
            if name[0] == "*":
                continue
            # analyze dependencies
            fullname = f"{basename}.{name[0]}"
            if fullname.find(".") > -1:
                try:
                    fullname = astroid.modutils.get_module_part(fullname, context_file)
                except ImportError:
                    continue
            if fullname != basename:
                self._imported_module(node, fullname, relative)

    def compute_module(self, context_name, mod_path):
        """return true if the module should be added to dependencies"""
        package_dir = os.path.dirname(self.project.path)
        if context_name == mod_path:
            return 0
        if astroid.modutils.is_standard_module(mod_path, (package_dir,)):
            return 1
        return 0

    def _imported_module(self, node, mod_path, relative):
        """Notify an imported module, used to analyze dependencies"""
        module = node.root()
        context_name = module.name
        if relative:
            mod_path = "{}.{}".format(".".join(context_name.split(".")[:-1]), mod_path)
        if self.compute_module(context_name, mod_path):
            # handle dependencies
            if not hasattr(module, "depends"):
                module.depends = []
            mod_paths = module.depends
            if mod_path not in mod_paths:
                mod_paths.append(mod_path)


class Project:
    """a project handle a set of modules / packages"""

    def __init__(self, name=""):
        self.name = name
        self.path = None
        self.modules = []
        self.locals = {}
        self.__getitem__ = self.locals.__getitem__
        self.__iter__ = self.locals.__iter__
        self.values = self.locals.values
        self.keys = self.locals.keys
        self.items = self.locals.items

    def add_module(self, node):
        self.locals[node.name] = node
        self.modules.append(node)

    def get_module(self, name):
        return self.locals[name]

    def get_children(self):
        return self.modules

    def __repr__(self):
        return f"<Project {self.name!r} at {id(self)} ({len(self.modules)} modules)>"


def project_from_files(
    files, func_wrapper=_astroid_wrapper, project_name="no name", black_list=("CVS",)
):
    """return a Project from a list of files or modules"""
    # build the project representation
    astroid_manager = astroid.manager.AstroidManager()
    project = Project(project_name)
    for something in files:
        if not os.path.exists(something):
            fpath = astroid.modutils.file_from_modpath(something.split("."))
        elif os.path.isdir(something):
            fpath = os.path.join(something, "__init__.py")
        else:
            fpath = something
        ast = func_wrapper(astroid_manager.ast_from_file, fpath)
        if ast is None:
            continue
        project.path = project.path or ast.file
        project.add_module(ast)
        base_name = ast.name
        # recurse in package except if __init__ was explicitly given
        if ast.package and something.find("__init__") == -1:
            # recurse on others packages / modules if this is a package
            for fpath in astroid.modutils.get_module_files(
                os.path.dirname(ast.file), black_list
            ):
                ast = func_wrapper(astroid_manager.ast_from_file, fpath)
                if ast is None or ast.name == base_name:
                    continue
                project.add_module(ast)
    return project
