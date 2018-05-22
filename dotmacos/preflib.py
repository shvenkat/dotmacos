import enum
import datetime
import numbers
import os
from pathlib import Path
import plistlib
from pprint import pformat
import subprocess
import tempfile
from typing import (Any, ByteString, cast, Container, Dict, FrozenSet, Optional,
                    Sequence)
import xml.parsers.expat as expat

import pyjson5


class FileFormat(enum.Enum):
    json5 = enum.auto()
    json = enum.auto()
    yaml = enum.auto()


IS_ROOT_USER = os.geteuid() == 0
ALL_SECTIONS: FrozenSet[str] = frozenset(["user", "local", "system"])
ACCESSIBLE_SECTIONS: FrozenSet[str] = frozenset(
    ["system"] if IS_ROOT_USER else ["user", "local"])


class Prefs(Dict):

    def __new__(cls, mapping: Dict[str, Any]) -> "Prefs":
        # Check that mapping is a dictionary.
        if not isinstance(mapping, dict):
            raise ValueError("Invalid prefs: not a mapping.")
        # Check keys are valid pref keys.
        if not all(isinstance(key, str) for key in mapping):
            raise ValueError("Invalid preference keys: {}".format(
                ", ".join(key for key in mapping
                          if not isinstance(key, str))))
        # Check values are valid pref values.
        if not all(cls._is_valid_value(value) for value in mapping.values()):
            raise ValueError("Invalid preference values:\n{}".format(
                "\n".join(pformat(value) for value in mapping.values()
                          if not cls._is_valid_value(value))))
        self = dict.__new__(cls, mapping)
        return cast(Prefs, self)

    @staticmethod
    def merge(*, old: "Prefs", new: "Prefs") -> "Prefs":
        """Merge two Prefs dictionaries. Values in `new` take precedence.

        For each key present in both `new` and `old`, the merged value is
        calculated as follows:

        Old value  New value  Merged value
        ---------  ---------  ------------
        <any>      scalar N   scalar N
        <any>      array N    array N
        dict O     dict N     dict M (union of keys; dict N values preferred)
        <other>    dict N     dict N
        """
        result = dict(old)
        for new_key, new_value in new.items():
            if (new_key in old and
                    isinstance(new_value, dict) and
                    isinstance(old[new_key], dict)):
                # Merge dictionaries with new values taking precedence.
                result[new_key] = dict(old[new_key])
                result[new_key].update(new_value)
            else:
                # Replace old value with new one, even for arrays.
                result[new_key] = new_value
        return Prefs(result)

    @staticmethod
    def diff_types(*, old: "Prefs", new: "Prefs") -> str:
        shared_keys = set(new.keys()).intersection(set(old.keys()))
        diff_types = [(key, type(old[key]), type(new[key]))
                      for key in shared_keys
                      if not isinstance(new[key], type(old[key]))]
        return "\n".join(["{key}: {old} -> {new}".format(key = key,
                                                         old = str(old_type),
                                                         new = str(new_type))
                          for key, old_type, new_type in diff_types])

    @staticmethod
    def diff(*, old: "Prefs", new: "Prefs") -> str:
        adds = ["<absent> -> {key}: {value}".format(key = key, value = value)
                for key, value in new.items()
                if key not in old]
        modifs = [("{key}: {old} -> {new}"
                   .format(key = key, old = str(old[key]), new = value)
                   if isinstance(value, type(old[key])) else
                   "{key}: ({old_type}) {old} -> ({new_type}) {new}"
                   .format(key = key, old = str(old[key]), new = value,
                           old_type = type(old[key]).__name__,
                           new_type = type(value).__name__))
                  for key, value in new.items()
                  if key in old and value != old[key]]
        return "\n".join(adds + modifs)

    @classmethod
    def from_os(cls, *, section: str, domain: str,
                keys: Optional[Container[str]] = None) -> "Prefs":
        if not cls._is_accessible(section):
            raise Exception("Cannot access {section} settings as user {uid}"
                            .format(section = section, uid = os.geteuid()))
        plist_fd, plist_name = tempfile.mkstemp(suffix = ".plist")
        cmd = (["defaults"] +
               (["-currentHost"] if section == "local" else []) +
               ["export", domain, plist_name])
        export_proc = subprocess.run(
            cmd,
            stdin = subprocess.DEVNULL,
            stdout = subprocess.PIPE,
            stderr = subprocess.PIPE)
        if export_proc.returncode != 0 or len(export_proc.stderr) > 0:
            raise OSError(
                "Failed to read current {section} settings for {domain}: "
                "'{cmd}' exited with status {status}, stdout '{stdout}' "
                "and stderr '{stderr}'"
                .format(section = section, domain = domain,
                        cmd = " ".join(cmd),
                        status = export_proc.returncode,
                        stdout = export_proc.stdout.decode(),
                        stderr = export_proc.stderr.decode()))
        try:
            with open(plist_name, "rb") as plist_file:
                keyvalue: Dict[str, Any] = plistlib.load(
                    plist_file, use_builtin_types = True)
        except FileNotFoundError:
            raise Exception("Internal error reading exported settings.")
        except (plistlib.InvalidFileException,  # type: ignore
                expat.ExpatError) as e:
            raise Exception("Internal error parsing exported settings.")
        os.close(plist_fd)
        os.remove(plist_name)
        if keys is None:
            prefs = Prefs(keyvalue)
        else:
            prefs = Prefs({key: value
                           for key, value in keyvalue.items()
                           if key in keys})
        return prefs

    def to_os(self, *, section: str, domain: str) -> None:
        if not self._is_accessible(section):
            raise Exception("Cannot access {section} settings as user {uid}"
                            .format(section = section, uid = os.geteuid()))
        with tempfile.NamedTemporaryFile("wb", suffix = ".plist") as plist_file:
            try:
                plistlib.dump(self, plist_file, fmt = plistlib.FMT_BINARY)
            except (FileNotFoundError, PermissionError,
                    TypeError, OverflowError) as e:
                raise Exception("Internal error writing settings: " + str(e))
            plist_file.flush()
            os.sync()
            cmd = (["defaults"] +
                   (["-currentHost"] if section == "local" else []) +
                   ["import", domain, plist_file.name])
            import_proc = subprocess.run(
                cmd,
                stdin = subprocess.DEVNULL,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE)
            if import_proc.returncode != 0 or len(import_proc.stderr) > 0:
                raise OSError(
                    "Failed to write new {section} settings for {domain}: "
                    "'{cmd}' exited with status {status}, stdout '{stdout}' "
                    "and stderr '{stderr}'"
                    .format(section = section, domain = domain,
                            cmd = " ".join(cmd),
                            status = import_proc.returncode,
                            stdout = import_proc.stdout,
                            stderr = import_proc.stderr))

    @classmethod
    def _is_valid_value(cls, value: Any) -> bool:
        """True if value is a valid plist value. See
        https://en.wikipedia.org/wiki/Property_list#Mac_OS_X."""
        if isinstance(value, (bool, numbers.Real, datetime.datetime, str,
                              ByteString)):
            return True
        elif isinstance(value, Sequence):
            return all(cls._is_valid_value(x) for x in value)
        elif isinstance(value, Dict):
            return all((isinstance(k, str) and cls._is_valid_value(v))
                       for k, v in value.items())
        else:
            return False

    @staticmethod
    def _is_accessible(section: str) -> bool:
        return ((section in ["user", "local"] and not IS_ROOT_USER) or
                (section in ["system"] and IS_ROOT_USER))


class Domains(Dict):

    def __new__(cls, mapping: Dict[str, Any]) -> "Domains":
        # Check that mapping is a dictionary.
        if not isinstance(mapping, dict):
            raise ValueError("Invalid domains: not a mapping.")
        # Check keys are valid domain names.
        if not all(isinstance(key, str) for key in mapping):
            raise ValueError("Invalid domain names: {}".format(
                ", ".join(key for key in mapping
                          if not isinstance(key, str))))
        # Check values are valid Prefs objects.
        self = dict.__new__(
            cls, {domain: Prefs(prefs)
                  for domain, prefs in mapping.items()})
        return cast(Domains, self)


class Sections(Dict):

    def __new__(cls, mapping: Dict[str, Any]) -> "Sections":
        # Check that mapping is a dictionary.
        if not isinstance(mapping, dict):
            raise ValueError("Invalid sections: not a mapping.")
        # Check keys are valid section names.
        if not all(key in ALL_SECTIONS for key in mapping):
            raise ValueError("Invalid section names: {}".format(
                ", ".join(key for key in mapping
                          if key not in ALL_SECTIONS)))
        # Check values are valid Domains objects.
        self = dict.__new__(
            cls, {section: Domains(domains)
                  for section, domains in mapping.items()})
        return cast(Sections, self)

    def diff_with_os(self, os_is_base: bool, all_keys: bool = False) -> str:

        def diff_domain(section: str, domain: str, prefs: Prefs) -> str:
            if os_is_base:
                diff = Prefs.diff(
                    old = Prefs.from_os(section = section, domain = domain),
                    new = prefs)
            else:
                diff = Prefs.diff(
                    old = prefs,
                    new = Prefs.from_os(
                        section = section, domain = domain,
                        keys = None if all_keys else prefs.keys()))
            return ("{domain}:\n{diff}"
                    .format(domain = domain,
                            diff = "  " + diff.replace("\n", "\n  "))
                    if len(diff) > 0 else
                    "")

        def diff_section(section: str, domains: Domains) -> str:
            diff = "\n".join(filter(lambda e: len(e) > 0,
                                    [diff_domain(section, domain, prefs)
                                     for domain, prefs in domains.items()]))
            return ("{section}:\n{diff}"
                    .format(section = section,
                            diff = "  " + diff.replace("\n", "\n  "))
                    if len(diff) > 0 else
                    "")

        return "\n".join(filter(lambda e: len(e) > 0,
                                [diff_section(section, domains)
                                 for section, domains in self.items()
                                 if section in ACCESSIBLE_SECTIONS]))

    def merge_from_os(self, all_keys: bool = False) -> "Sections":
        return Sections(
            {section:
                ({domain: Prefs.merge(
                    old = prefs,
                    new = Prefs.from_os(
                        section = section,
                        domain = domain,
                        keys = None if all_keys else prefs.keys()))
                  for domain, prefs in domains.items()}
                 if section in ACCESSIBLE_SECTIONS else
                 domains)
             for section, domains in self.items()})

    def merge_to_os(self) -> None:
        for section, domains in self.items():
            if section in ACCESSIBLE_SECTIONS:
                for domain, prefs in domains.items():
                    (Prefs.merge(old = Prefs.from_os(section = section,
                                                     domain = domain),
                                 new = prefs)
                     .to_os(section = section, domain = domain))

    @classmethod
    def from_config_file(cls, path: Path, *, file_format: FileFormat,
                         include_sections: Container[str] = ALL_SECTIONS,
                         ) -> "Sections":
        if file_format == FileFormat.json5:
            sections = cls._read_json5(path)
        elif file_format == FileFormat.json:
            sections = cls._read_json(path)
        elif file_format == FileFormat.yaml:
            sections = cls._read_yaml(path)
        else:
            raise ValueError(
                "Invalid config format: {}".format(file_format.name))
        return Sections({section: value for section, value in sections.items()
                         if section in include_sections})

    @classmethod
    def _read_json5(cls, path: Path) -> Dict[str, Any]:
        with open(path.as_posix(), "rt") as file_handle:
            data = pyjson5.load(file_handle)
        if cls._is_valid_data(data):
            return cast(Dict[str, Any], data)
        else:
            raise ValueError(
                "Invalid data in config file {}".format(path.as_posix()))

    @classmethod
    def _read_json(cls, path: Path) -> Dict[str, Any]:
        raise NotImplementedError()

    @classmethod
    def _read_yaml(cls, path: Path) -> Dict[str, Any]:
        raise NotImplementedError()

    @staticmethod
    def _is_valid_data(data: Any) -> bool:
        return (isinstance(data, dict) and
                all(isinstance(key, str) for key in data))

    def to_config_file(self, path: Path, file_format: FileFormat) -> None:
        if file_format == FileFormat.json5:
            self._write_json5(path)
        elif file_format == FileFormat.json:
            self._write_json(path)
        elif file_format == FileFormat.yaml:
            self._write_yaml(path)
        else:
            raise ValueError(
                "Invalid config format: {}".format(file_format.name))

    def _write_json5(self, path: Path) -> None:
        with open(path.as_posix(), "wt") as file_handle:
            pyjson5.dump(self, file_handle)

    def _write_json(self, path: Path) -> None:
        raise NotImplementedError()

    def _write_yaml(self, path: Path) -> None:
        raise NotImplementedError()
