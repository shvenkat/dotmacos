import enum
import datetime
import numbers
from pprint import pformat
from types import MappingProxyType
from typing import Any, ByteString, Dict, Sequence


class Section(enum.Enum):
    user = enum.auto()
    local = enum.auto()
    system = enum.auto()


class Sections(MappingProxyType):

    def __new__(cls, mapping: Dict[str, Any]) -> "Sections":
        # Check that mapping is a dictionary.
        if not isinstance(mapping, dict):
            raise ValueError("Invalid sections: not a mapping.")
        # Check keys are valid section names.
        valid_section_names = frozenset(Section.__members__.keys())
        if not all(key in valid_section_names for key in mapping):
            raise ValueError("Invalid section names: {}".format(
                ", ".join(key for key in mapping
                          if key not in valid_section_names)))
        # Check values are valid Domains objects.
        self = MappingProxyType({section: Domains(domains)
                                 for section, domains in mapping.items()})
        return self  # type: ignore


class Domains(MappingProxyType):

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
        self = MappingProxyType({domain: Prefs(prefs)
                                 for domain, prefs in mapping.items()})
        return self  # type: ignore


class Prefs(MappingProxyType):

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
        if not all(is_valid(value) for value in mapping.values()):
            raise ValueError("Invalid preference values:\n{}".format(
                "\n".join(pformat(value) for value in mapping.values()
                          if not is_valid(value))))
        return mapping  # type: ignore


def is_valid(value: Any) -> bool:
    """True if value is a valid plist value. See
    https://en.wikipedia.org/wiki/Property_list#Mac_OS_X."""
    if isinstance(value, (bool, numbers.Real, datetime.datetime, str,
                          ByteString)):
        return True
    elif isinstance(value, Sequence):
        return all(is_valid(x) for x in value)
    elif isinstance(value, Dict):
        return all((isinstance(k, str) and is_valid(v))
                   for k, v in value.items())
    else:
        return False
