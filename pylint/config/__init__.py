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
import sys

import appdirs

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

def _resolve_pylint_home():
    env_home = os.environ.get("PYLINTHOME")
    if env_home:
        return env_home

    try:
        cache_dir = appdirs.user_cache_dir("pylint")
    except Exception:  # pylint: disable=broad-except
        cache_dir = ""

    if cache_dir:
        cache_dir = os.path.abspath(cache_dir)
        if os.path.isabs(cache_dir):
            return cache_dir

    return ".pylint.d"


def _legacy_pylint_homes(current_home):
    homes = []
    user_home = os.path.expanduser("~")
    if user_home != "~":
        homes.append(os.path.join(user_home, ".pylint.d"))
    homes.append(os.path.join(os.getcwd(), ".pylint.d"))

    current_normalized = os.path.abspath(current_home)
    seen = set()
    legacy_homes = []
    for home in homes:
        normalized = os.path.abspath(home)
        if normalized == current_normalized or normalized in seen:
            continue
        seen.add(normalized)
        legacy_homes.append(home)
    return legacy_homes


PYLINT_HOME = _resolve_pylint_home()


def _get_pdata_path(base_name, recurs):
    base_name = base_name.replace(os.sep, "_")
    return os.path.join(PYLINT_HOME, f"{base_name}{recurs}.stats")


def load_results(base):
    data_file = _get_pdata_path(base, 1)
    try:
        with open(data_file, "rb") as stream:
            return pickle.load(stream)
    except FileNotFoundError:
        pass
    except Exception:  # pylint: disable=broad-except
        return {}

    if "PYLINTHOME" in os.environ:
        return {}

    legacy_base = base.replace(os.sep, "_")
    for legacy_home in _legacy_pylint_homes(PYLINT_HOME):
        legacy_file = os.path.join(legacy_home, f"{legacy_base}1.stats")
        try:
            with open(legacy_file, "rb") as stream:
                return pickle.load(stream)
        except FileNotFoundError:
            continue
        except Exception:  # pylint: disable=broad-except
            return {}

    return {}


def save_results(results, base):
    try:
        os.makedirs(PYLINT_HOME, exist_ok=True)
    except OSError:
        print("Unable to create directory %s" % PYLINT_HOME, file=sys.stderr)
        return
    data_file = _get_pdata_path(base, 1)
    try:
        with open(data_file, "wb") as stream:
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
not found, it defaults to the user cache directory reported by the operating
system (for instance ~/.cache/pylint). If this location cannot be resolved,
Pylint stores data in ./.pylint.d.
    * PYLINTRC
    Path to the configuration file. See the documentation for the method used
to search for configuration file.
"""
    % globals()  # type: ignore
)
