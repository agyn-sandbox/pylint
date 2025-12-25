# Copyright (c) 2006-2010, 2012-2014 LOGILAB S.A. (Paris, FRANCE) <contact@logilab.fr>
# Copyright (c) 2008 pyves@crater.logilab.fr <pyves@crater.logilab.fr>
# Copyright (c) 2013 Google, Inc.
# Copyright (c) 2013 John McGehee <jmcgehee@altera.com>
# Copyright (c) 2014-2020 Claudiu Popa <pcmanticore@gmail.com>
# Copyright (c) 2014 Brett Cannon <brett@python.org>
# Copyright (c) 2014 Arun Persaud <arun@nubati.net>
# Copyright (c) 2015 Aru Sahni <arusahni@gmail.com>
# Copyright (c) 2015 John Kirkham <jakirkham@gmail.com>
# Copyright (c) 2015 Ionel Cristian Maries <contact@ionelmc.ro>
# Copyright (c) 2016 Erik <erik.eriksson@yahoo.com>
# Copyright (c) 2016 Alexander Todorov <atodorov@otb.bg>
# Copyright (c) 2016 Moises Lopez <moylop260@vauxoo.com>
# Copyright (c) 2017, 2020 hippo91 <guillaume.peillex@gmail.com>
# Copyright (c) 2017-2019 Ville Skyttä <ville.skytta@iki.fi>
# Copyright (c) 2017 ahirnish <ahirnish@gmail.com>
# Copyright (c) 2017 Łukasz Rogalski <rogalski.91@gmail.com>
# Copyright (c) 2018, 2020 Anthony Sottile <asottile@umich.edu>
# Copyright (c) 2018 Jim Robertson <jrobertson98atx@gmail.com>
# Copyright (c) 2018 ssolanki <sushobhitsolanki@gmail.com>
# Copyright (c) 2018 Bryce Guinta <bryce.paul.guinta@gmail.com>
# Copyright (c) 2018 Sushobhit <31987769+sushobhit27@users.noreply.github.com>
# Copyright (c) 2018 Gary Tyler McLeod <mail@garytyler.com>
# Copyright (c) 2018 Konstantin <Github@pheanex.de>
# Copyright (c) 2018 Nick Drozd <nicholasdrozd@gmail.com>
# Copyright (c) 2019-2021 Pierre Sassoulas <pierre.sassoulas@gmail.com>
# Copyright (c) 2019 Janne Rönkkö <jannero@users.noreply.github.com>
# Copyright (c) 2019 Ashley Whetter <ashley@awhetter.co.uk>
# Copyright (c) 2019 Hugo van Kemenade <hugovk@users.noreply.github.com>
# Copyright (c) 2021 Marc Mueller <30130371+cdce8p@users.noreply.github.com>

# Licensed under the GPL: https://www.gnu.org/licenses/old-licenses/gpl-2.0.html
# For details: https://github.com/PyCQA/pylint/blob/main/LICENSE

import os
import pickle
import shutil
import sys
import warnings
from pathlib import Path
from typing import Optional, Type

from platformdirs import user_data_dir

from pylint.config.configuration_mixin import ConfigurationMixIn
from pylint.config.find_default_config_files import find_default_config_files
from pylint.config.man_help_formatter import _ManHelpFormatter
from pylint.config.option import Option
from pylint.config.option_manager_mixin import OptionsManagerMixIn
from pylint.config.option_parser import OptionParser
from pylint.config.options_provider_mixin import OptionsProviderMixIn, UnsupportedAction

__all__ = [
    "ConfigurationMixIn",
    "find_default_config_files",
    "_ManHelpFormatter",
    "Option",
    "OptionsManagerMixIn",
    "OptionParser",
    "OptionsProviderMixIn",
    "UnsupportedAction",
]

LEGACY_DATA_DIR_NAME = ".pylint.d"
MIGRATION_SENTINEL = ".pylint-legacy-migrated"


def _resolve_home() -> Optional[Path]:
    expanded = Path(os.path.expanduser("~"))
    if str(expanded) == "~":
        return None
    return expanded


def _legacy_directory(home_path: Optional[Path]) -> Path:
    if home_path is None:
        return Path(LEGACY_DATA_DIR_NAME)
    return home_path / LEGACY_DATA_DIR_NAME


def _warn(message: str, category: Type[Warning] = UserWarning) -> None:
    warnings.warn(message, category, stacklevel=3)


def _prepare_data_directory(target: Path, legacy: Path) -> Path:
    sentinel = target / MIGRATION_SENTINEL

    if target.exists():
        if target.is_dir():
            return target
        _warn(
            f"Pylint data path '{target}' exists but is not a directory. "
            f"Falling back to legacy location '{legacy}'."
        )
        try:
            legacy.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            _warn(
                f"Unable to create legacy Pylint data directory '{legacy}': {error}. "
                "Persistent data will be disabled for this run."
            )
        return legacy

    try:
        target.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        _warn(
            f"Unable to create Pylint data directory '{target}': {error}. "
            f"Falling back to legacy location '{legacy}'."
        )
        try:
            legacy.mkdir(parents=True, exist_ok=True)
        except OSError as legacy_error:
            _warn(
                f"Unable to create legacy Pylint data directory '{legacy}': {legacy_error}. "
                "Persistent data will be disabled for this run."
            )
        return legacy

    if legacy.exists() and not sentinel.exists():
        try:
            for item in legacy.iterdir():
                destination = target / item.name
                if item.is_dir():
                    shutil.copytree(str(item), str(destination))
                else:
                    shutil.copy2(str(item), str(destination))
        except OSError as error:
            _warn(
                f"Unable to migrate data from '{legacy}' to '{target}': {error}. "
                f"Using legacy directory for this run."
            )
            shutil.rmtree(str(target), ignore_errors=True)
            try:
                legacy.mkdir(parents=True, exist_ok=True)
            except OSError as legacy_error:
                _warn(
                    f"Unable to create legacy Pylint data directory '{legacy}': {legacy_error}. "
                    "Persistent data will be disabled for this run."
                )
            return legacy
        try:
            sentinel.touch(exist_ok=True)
        except OSError as error:
            _warn(
                f"Unable to create migration sentinel '{sentinel}': {error}."
            )
        _warn(
            f"Pylint persistent data migrated from '{legacy}' to '{target}'."
        )

    return target


def get_pylint_data_dir() -> str:
    override = os.environ.get("PYLINTHOME")
    if override:
        return override

    home_path = _resolve_home()
    if home_path is None:
        fallback = Path(LEGACY_DATA_DIR_NAME)
        try:
            fallback.mkdir(parents=True, exist_ok=True)
        except OSError as error:
            _warn(
                f"Unable to create fallback Pylint data directory '{fallback}': {error}. "
                "Persistent data will be disabled for this run."
            )
        _warn(
            "HOME directory could not be resolved. Falling back to './.pylint.d'. "
            "This fallback is deprecated and will be removed in a future release.",
            DeprecationWarning,
        )
        return str(fallback)

    data_directory = Path(user_data_dir(appname="pylint"))
    legacy_directory = _legacy_directory(home_path)
    resolved_directory = _prepare_data_directory(data_directory, legacy_directory)
    return str(resolved_directory)


USER_HOME = os.path.expanduser("~")
PYLINT_HOME = get_pylint_data_dir()
if "PYLINTHOME" in os.environ and USER_HOME == "~":
    USER_HOME = os.path.dirname(PYLINT_HOME)


def _get_pdata_path(base_name, recurs):
    base_name = base_name.replace(os.sep, "_")
    return Path(PYLINT_HOME) / f"{base_name}{recurs}.stats"


def load_results(base):
    data_file = _get_pdata_path(base, 1)
    try:
        with data_file.open("rb") as stream:
            return pickle.load(stream)
    except Exception:  # pylint: disable=broad-except
        return {}


def save_results(results, base):
    data_directory = Path(PYLINT_HOME)
    try:
        data_directory.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        print(f"Unable to create directory {data_directory}: {error}", file=sys.stderr)
        return

    data_file = _get_pdata_path(base, 1)
    try:
        with data_file.open("wb") as stream:
            pickle.dump(results, stream)
    except OSError as ex:
        print(f"Unable to create file {data_file}: {ex}", file=sys.stderr)


def find_pylintrc():
    """search the pylint rc file and return its path if it find it, else None"""
    for config_file in find_default_config_files():
        if config_file.endswith("pylintrc"):
            return config_file

    return None


PYLINTRC = find_pylintrc()

ENV_HELP = (
    """
The following environment variables are used:
    * PYLINTHOME
    Path to the directory where persistent data for the run will be stored. If
unset, Pylint uses the user data directory defined by the operating system via
the XDG Base Directory specification. Data from the legacy ~/.pylint.d
directory is migrated automatically. If the home directory cannot be
determined, the fallback is ./.pylint.d (deprecated).
    * PYLINTRC
    Path to the configuration file. See the documentation for the method used
to search for configuration file.
"""
    % globals()  # type: ignore
)
