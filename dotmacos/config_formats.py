from pathlib import Path
import enum
import pyjson5
from typing import Any, Dict, FrozenSet

from .types import Section, Sections


ALL_SECTIONS = frozenset(Section.__members__.keys())


class FileFormat(enum.Enum):
    json5 = enum.auto()
    json = enum.auto()
    yaml = enum.auto()


def read_config_file(path: Path, config_format: FileFormat,
                     include_sections: FrozenSet[str] = ALL_SECTIONS,
                     ) -> Sections:
    if config_format == FileFormat.json5:
        sections = read_json5(path)
    elif config_format == FileFormat.json:
        sections = read_json(path)
    elif config_format == FileFormat.yaml:
        sections = read_yaml(path)
    else:
        raise ValueError("Invalid config format: {}".format(config_format.name))
    return Sections({section: value for section, value in sections.items()
                     if section in include_sections})


def read_json5(path: Path) -> Dict[str, Any]:
    with open(path.as_posix(), "rt") as file_handle:
        data = pyjson5.load(file_handle)
    if is_valid_data(data):
        return data  # type: ignore
    else:
        raise ValueError(
            "Invalid data in config file {}".format(path.as_posix()))


def read_json(path: Path) -> Dict[str, Any]:
    raise NotImplementedError()


def read_yaml(path: Path) -> Dict[str, Any]:
    raise NotImplementedError()


def is_valid_data(data: Any) -> bool:
    return isinstance(data, dict) and all(isinstance(key, str) for key in data)
