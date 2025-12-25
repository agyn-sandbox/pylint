# pylint: disable=missing-docstring,import-outside-toplevel,reimported,redefined-outer-name

import abc
from abc import ABC
import abc as module_abc
from abc import ABC as ModuleAbc


MODULE_TYPE_COMMENT = None  # type: abc.ABC
MODULE_TYPE_NAME = None  # type: ABC
MODULE_ALIAS_TYPE_COMMENT = None  # type: module_abc.ABC
MODULE_ALIAS_TYPE_NAME = None  # type: ModuleAbc


def module_values():
    return (
        MODULE_TYPE_COMMENT,
        MODULE_TYPE_NAME,
        MODULE_ALIAS_TYPE_COMMENT,
        MODULE_ALIAS_TYPE_NAME,
    )


def function_type_comments():
    import abc
    from abc import ABC

    func_module_comment = None  # type: abc.ABC
    func_name_comment = None  # type: ABC

    return func_module_comment, func_name_comment


def function_alias_type_comments():
    import abc as func_abc
    from abc import ABC as FuncAbc

    func_alias_module_comment = None  # type: func_abc.ABC
    func_alias_name_comment = None  # type: FuncAbc

    return func_alias_module_comment, func_alias_name_comment
