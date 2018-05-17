# from argparse import ArgumentParser
# import datetime
# from functools import lru_cache
# import numbers
# import os
# from pathlib import Path
# import plistlib
# import re
# import string
# import subprocess
# import sys
# from typing import (Any, ByteString, Dict, Mapping, Optional, Sequence, Set,
#                     TextIO, Union)
# import xml.parsers.expat as expat

# try:
#     import yaml
# except ImportError:
#     from subprocess import run, SubprocessError
#     try:
#         run(["pip3", "install", "pyyaml"], check = True)
#     except (OSError, SubprocessError):
#         sys.stderr.write(
#             "Error: Installation of required python yaml package failed.\n")
#         sys.exit(1)
#     else:
#         import yaml


# PROGRAM = sys.argv[0]
# NAME = Path(PROGRAM).name


# def main() -> None:
#     """Parse arguments and dispatch appropriately."""
#     # Parse arguments.
#     parser = CustomArgumentParser()
#     subparsers = parser.add_subparsers(dest = "subcommand")
#     subparsers.add_parser("help").add_argument("topic", nargs = "?")
#     subparsers.add_parser("load")
#     parser_dump = subparsers.add_parser("dump")
#     parser_dump.add_argument("--filter", type = Path,
#                              help = "Only dump keys present in a YAML.")
#     args = parser.parse_args()

#     # Dispatch appropriately.
#     if args.subcommand is None:
#         sys.stderr.write(USAGE)
#     elif args.subcommand == "help":
#         if args.topic is None:
#             sys.stderr.write(USAGE)
#         elif args.topic == "load":
#             sys.stderr.write(HELP_LOAD + HELP_YAML)
#         elif args.topic == "dump":
#             sys.stderr.write(HELP_DUMP + HELP_YAML)
#         else:
#             error(2, "unrecognized help topic: " + args.topic)
#     elif args.subcommand == "load":
#         load()
#     elif args.subcommand == "dump":
#         dump(args.filter)
#     else:
#         error(2, "unrecognized sub-command: " + args.subcommand)


# def load() -> None:
#     """Load/set preferences from YAML on stdin, after merging with current
#     preferences."""
#     desired_prefs = read_pref()
#     for category, domains in desired_prefs.items():
#         if category == "system" and os.geteuid() != 0:
#             # System preference files must be owned by root. To write these
#             # files, acquire root access by invoking this program via `sudo`.
#             get_sudo()
#             try:
#                 subprocess.run(["sudo", PROGRAM, "load"],
#                                input = yaml.dump({category: domains}),
#                                stderr = subprocess.PIPE,
#                                universal_newlines = True, check = True)
#             except subprocess.CalledProcessError as e:
#                 sys.stderr.write(e.stderr.decode())
#                 sys.exit(e.returncode)
#         elif category != "system" and os.geteuid() == 0:
#             # User preference files must be owned by the user; don't write these
#             # as root.
#             error(2, "incorrect usage. Do not run this program as root when"
#                      "setting user (non-privileged) preferences.")
#         else:
#             # Set preferences, after merging with current settings.
#             load_category(category, domains)


# def dump(filter_by: Optional[Path] = None) -> None:
#     """Dump current preferences to YAML on stdout, optionally filtering the
#     output."""
#     filter_prefs = read_filter(filter_by)
#     pref = {}  # type: Dict[str, Any]
#     for category, domains in filter_prefs.items():
#         try:
#             category_pref = dump_category(category, domains)
#         except PermissionError as e:
#             if category == "system" and os.geteuid() != 0:
#                 # Acquire root access by invoking this program via `sudo`.
#                 get_sudo()
#                 try:
#                     output = subprocess.run(["sudo", PROGRAM, "dump", "--filter", "-"],
#                                             input = yaml.dump({category: domains}),
#                                             stdout = subprocess.PIPE, stderr = subprocess.PIPE,
#                                             universal_newlines = True, check = True).stdout
#                 except subprocess.CalledProcessError as cpe:
#                     sys.stderr.write(cpe.stderr.decode())
#                     sys.exit(cpe.returncode)
#                 try:
#                     category_pref = yaml.safe_load(output)[category]
#                 except TypeError:
#                     category_pref = None
#                 except KeyError:
#                     error(1, "invalid result found when dumping privileged (system) preferences.")
#             else:
#                 error(1, "failed to dump preferences for the {} category.".format(category), e)
#         if category_pref is not None:
#             pref[category] = category_pref
#     if len(pref) > 0:
#         write_pref(pref, sys.stdout)


# Category = str
# Domain = str
# Key = str
# Scalar = Union[bool, numbers.Real, datetime.datetime, str, ByteString]
# Value = Union[Scalar, Sequence[Scalar], Dict[str, Scalar]]
# # The intended type definition below cannot be succinctly expressed in Python 3.6.0 using type
# # aliases, union types and forward references.
# # Value = Union[Scalar, Sequence[Value], Mapping[str, Value]]
# KeyValue = Mapping[Key, Value]
# Pref = Mapping[Category, Mapping[Domain, KeyValue]]
# Filter = Mapping[Category, Optional[Mapping[Domain, Optional[Mapping[Key, Optional[Value]]]]]]


# def read_pref() -> Pref:
#     """Parses and validates preferences."""
#     try:
#         pref = yaml.safe_load(sys.stdin)
#     except yaml.YAMLError as e:
#         error(1, "invalid YAML in input.", e)
#     if not valid_pref(pref):
#         error(1, "invalid structure in input. See `{} help load` for details.".format(NAME))
#     for category, domains in pref.items():
#         for domain, keyvalue in domains.items():
#             if not valid_keyvalue(keyvalue):
#                 error(1, "invalid structure in input. See `{} help load` for details.".format(NAME))
#     return pref


# def read_filter(path: Optional[Path]) -> Filter:
#     """Parses and validates filter."""
#     if path is None:
#         pref_filter = None  # type: Optional[Filter]
#     else:
#         try:
#             if str(path) == "-":
#                 pref_filter = yaml.safe_load(sys.stdin)
#             else:
#                 with open(path, "rt") as filter_file:
#                     pref_filter = yaml.safe_load(filter_file)
#         except FileNotFoundError:
#             error(1, "filter file not found: " + str(path))
#         except PermissionError as e:
#             error(1, "failed to read filter file: " + str(path), e)
#         except yaml.YAMLError as e:
#             error(1, "invalid YAML in filter.", e)
#     if pref_filter is None:
#         pref_filter = {k: None for k in plist_categories()}
#     if not valid_filter(pref_filter):
#         error(1, "filter does not have the required structure. See `{} help dump` for details."
#                  .format(NAME))
#     return pref_filter


# def write_pref(pref: Any, stream: TextIO) -> None:
#     """Validates and writes preferences as YAML."""
#     if not valid_pref(pref):
#         error(1, "invalid structure in internal data.")
#     for category, domains in pref.items():
#         for domain, keyvalue in domains.items():
#             if not valid_keyvalue(keyvalue):
#                 error(1, "invalid structure in internal data.")
#     yaml.dump(pref, stream, default_flow_style = False)


# def read_plist(category: Category, domain: Domain) -> Optional[KeyValue]:
#     """Parses and validates plist content. Raises PermissionError."""
#     path = plist_path(category, domain)
#     try:
#         with open(path, "rb") as plist_file:
#             keyvalue = plistlib.load(plist_file, use_builtin_types = True)  # type: Any
#     except FileNotFoundError:
#         return None
#     except (plistlib.InvalidFileException, expat.ExpatError) as e:  # type: ignore
#         error(1, "failed to parse plist file: " + str(path), e)
#     if not valid_keyvalue(keyvalue):
#         error(1, "unexpected structure in plist file: " + str(path))
#     return keyvalue


# def write_plist(category: Category, domain: Domain, keyvalue: KeyValue) -> None:
#     """Writes plist content."""
#     path = plist_path(category, domain)
#     try:
#         with open(path, "wb") as plist_file:
#             plistlib.dump(keyvalue, plist_file, fmt = plistlib.FMT_BINARY)
#     except FileNotFoundError as e:
#         error(1, "plist directory does not exist: " + os.path.dirname(path), e)  # type: ignore
#     except PermissionError as e:
#         error(1, "unable to write plist file: " + str(path), e)
#     except TypeError as e:
#         error(1, "unsupported plist type.", e)
#     except OverflowError as e:
#         error(1, "plist integer overflow.", e)


# def load_category(category: Category, domains: Mapping[Domain, KeyValue]) -> None:
#     """Load/set preferences for all domains in a single category."""
#     for domain, desired_keyvalue in domains.items():
#         try:
#             current_keyvalue = read_plist(category, domain)
#         except PermissionError as e:
#             error(1, "unable to read plist file: " + str(plist_path(category, domain)), e)
#         # Merge and set preferences.
#         write_plist(category, domain, merge(desired_keyvalue, current_keyvalue))


# def dump_category(category: Category,
#                   filter_domains: Optional[Mapping[Domain, Optional[Mapping[Key, Any]]]]
#                   ) -> Optional[Mapping[Domain, KeyValue]]:
#     """Dump preferences for all domains in a single category."""
#     domains = (current_domains(category)
#                if filter_domains is None else
#                current_domains(category).intersection(filter_domains.keys()))
#     category_pref = {}  # type: Dict[Domain, KeyValue]
#     for domain in domains:
#         keyvalue = read_plist(category, domain)
#         if keyvalue is None:
#             continue
#         if filter_domains is not None:
#             filter_keys = filter_domains[domain]
#             if filter_keys is not None:
#                 keyvalue = {key: value for key, value in keyvalue.items() if key in filter_keys}
#         if len(keyvalue) == 0:
#             continue
#         category_pref[domain] = keyvalue
#     return None if len(category_pref) == 0 else category_pref


# def valid_filter(prefs: Any) -> bool:
#     """True if prefs has the required structure i.e. a nested dictionary keyed first by valid
#     category, then by domain (string) and finally by preference key (string). Null values are
#     allowed."""
#     if not isinstance(prefs, dict):
#         return False
#     for category, domains in prefs.items():
#         if category not in plist_categories():
#             return False
#         if domains is None:
#             continue
#         if not isinstance(domains, dict):
#             return False
#         for domain, keys in domains.items():
#             if not isinstance(domain, str):
#                 return False
#             if keys is None:
#                 continue
#             if not isinstance(keys, dict):
#                 return False
#             for key, value in keys.items():
#                 if not isinstance(key, str):
#                     return False
#     return True


# def merge(desired: KeyValue, base: Optional[KeyValue]) -> KeyValue:
#     """Merge keys and values for a single domain. Values in `desired` take precedence.

#     For each key present in both `desired` and `base`, the final value is resolved as follows:

#     Desired value  Base value  Final value
#     -------------  ----------  -----------
#     scalar A       <any>       scalar A
#     array A        <any>       array A
#     dict A         dict B      dict C (union of keys; values from dict A take precedence)
#     dict A         <other>     dict A
#     """
#     if base is None:
#         return desired
#     result = dict(base)
#     for desired_key, desired_value in desired.items():
#         if (desired_key in base and
#                 isinstance(desired_value, dict) and isinstance(base[desired_key], dict)):
#             # Merge dictionaries with desired values taking precedence.
#             result[desired_key] = dict(base[desired_key])  # type: ignore
#             result[desired_key].update(desired_value)      # type: ignore
#         else:
#             # Log novel key.
#             result[desired_key] = desired_value
#     return result


# def plist_path(category: Category, domain: Domain) -> Path:
#     """Plist file path for a domain."""
#     if category == "local":
#         return plist_categories()[category] / "{}.{}.plist".format(domain, local_uuid())
#     else:
#         return plist_categories()[category] / "{}.plist".format(domain)


# def current_domains(category: Category) -> Set[Domain]:
#     """All plist file paths in a category."""
#     try:
#         files = set(x.name for x in plist_categories()[category].iterdir() if x.match("*.plist"))
#     except (FileNotFoundError, NotADirectoryError) as e:
#         error(1, "failed to locate current preferences for category " + category, e)
#     pattern = r"(.+).{}.plist".format(local_uuid()) if category == "local" else r"(.+).plist"
#     return set(m.group(1)
#                for m in (re.fullmatch(pattern, x) for x in files)
#                if m is not None)


# @lru_cache()
# def plist_categories() -> Mapping[Category, Path]:
#     """Maps categories to plist storage locations."""
#     try:
#         home = os.environ["HOME"]
#     except KeyError:
#         error(1, "cannot determine your home directory. Environment variable HOME not set.")
#     return {"user":   Path(home) / Path("Library/Preferences"),
#             "local":  Path(home) / Path("Library/Preferences/ByHost"),
#             "system": Path("/")  / Path("Library/Preferences")}


# @lru_cache()
# def local_uuid() -> str:
#     """Local machine UUID for use in naming plist file in the local category."""
#     try:
#         uuid = (re.search(r'^ *"IOPlatformUUID" = "([0-9A-Fa-f-]{36})"$',
#                           subprocess.run(["ioreg", "-r", "-d1", "-c", "IOPlatformExpertDevice"],
#                                          stdout = subprocess.PIPE, universal_newlines = True,
#                                          check = True).stdout,
#                           re.MULTILINE)
#                 .group(1))
#     except FileNotFoundError:
#         error(1, "cannot determine local machine UUID. Command 'ioreg' not found.")
#     except subprocess.CalledProcessError as e:
#         error(1, "cannot determine local machine UUID.", e)
#     except AttributeError:
#         error(1, "cannot determine local machine UUID. Failed to identify the UUID value for key"
#                  "IOPlatformExpertDevice from `ioreg -r -d1 -c IOPlatformExpertDevice`.")
#     return uuid


# def get_sudo() -> None:
#     """When this function returns, `sudo` may be invoked without a password prompt."""
#     if subprocess.run(["sudo", "-n", "-v"], stderr = subprocess.DEVNULL).returncode == 0:
#         return
#     info("Using sudo to access privileged (system) preferences. Enter your password.")
#     if subprocess.run(["sudo", "-v"]).returncode != 0:
#         error(1, "failed to acquire sudo access.")


# class CustomArgumentParser(ArgumentParser):
#     """Uses a custom fixed message for usage and help."""

#     def format_usage(self):
#         return USAGE

#     def format_help(self):
#         return USAGE

#     def error(self, message):
#         error(2, message)


# USAGE = string.Template("""
# Manage OSX/MacOS preferences with YAML.

# Usage:
#     $program -h|--help
#     $program help (load|dump)
#     $program load < desired_prefs.yaml
#     $program dump [--filter desired_prefs.yaml] > current_prefs.yaml

# Sub-commands:
#     help    Detailed help on load or dump.
#     load    Load/set preferences from YAML on stdin. Use `$program help load`
#             for details on the YAML structure and how preferences are merged.
#     dump    Dump current preferences to YAML on stdout. Use `$program help save`
#             for details on the YAML structure and how to filter the output.

# \033[1mNOTE\033[0m: Root access may be required to set and/or read privileged
# preferences i.e. the "system" category in the YAML structure. However, running
# this program as root (e.g. `sudo $program`) is not recommended. This program
# uses `sudo` internally, and only as needed, to acquire root access. You _may_
# be asked to enter your password.
# """).safe_substitute(program = NAME)


# HELP_LOAD = """
# \033[1mNOTE:\033[0m You may need to quit applications and/or logout/login for
# certain settings to take effect. Open applications can revert or overwrite
# settings loaded using this command.

# Preferences are read from standard input and must conform to the YAML structure
# described below. Multiple YAML documents in the input stream are not supported.

# \033[1mMERGING VALUES\033[0m

# The desired preference settings are merged with current settings before being
# written to the appropriate .plist files. The intention is to preserve current
# settings that do not conflict with the desired settings. For each key present in
# both the desired and current settings, the final value is resolved as follows.

# Desired value  Current value  Final value
# -------------  -------------  -----------
# scalar A       <any>          scalar A
# array A        <any>          array A
# dict A         dict B         dict C (union of keys; dict A values override B)
# dict A         <other>        dict A

# For array and dictionary values, the above behavior emulates the `-array` (not
# `-array-add`) and `-dict-add` (not `-dict`) parameters respectively, of
# `defaults write`.
# """


# HELP_DUMP = """
# Preferences are written to standard output and conform to the YAML structure
# described below. A single YAML document is generated, sorted by category,
# domain and key.

# Use `--filter prefs.yaml` to restrict the output to categories, domains and keys
# in `prefs.yaml`. For instance, the following filter YAML causes the output to
# exclude all system (privileged) settings, include all settings in the user
# category and only a single domain and key in the local category.

# local:
#   com.apple.screensaver:
#     showClock:

# user:
# """


# HELP_YAML = """
# \033[1mYAML STRUCTURE\033[0m

# category:
#   domain:
#     key: value

# Categories must be one of the strings from the table below. Domains and keys must be strings. Values
# may be of the following types: boolean, real number, string, ISO 8601 date, base64-encoded data,
# array, and dictionary with string keys. Array elements and dictionary values must have one of the
# above types. See https://en.wikipedia.org/wiki/Property_list#Mac_OS_X.

# Category  OS command                  Storage location
# --------  ----------                  ----------------
# user      defaults read               ~/Library/Preferences/<domain>.plist
# local     defaults -currentHost read  ~/Library/Preferences/ByHost/<domain>.<host-uuid>.plist
# system    sudo defaults read          /Library/Preferences/<domain>.plist

# \033[1mSAMPLE YAML\033[0m

# system:
#   .GlobalPreferences:  # NSGlobalDomain
#     AppleKeyboardUIMode: 2

# local:
#   com.apple.screensaver:
#     showClock: true

# user:
#   .GlobalPreferences:  # NSGlobalDomain
#     AppleLocale: en_US
#     AppleLanguages:
#     - en

#   com.apple.finder:
#     ShowPreviewPane: true
# """


# if __name__ == "__main__":
#     try:
#         main()
#     except SystemExit:
#         raise
#     except KeyboardInterrupt:
#         sys.stderr.write("\n")
#         sys.exit(1)
#     except BaseException as e:
#         error(1, exception = e)
