from configparser import ConfigParser
from pathlib import Path
import re
from setuptools import setup
from typing import List


PROJECT_NAME = "dotmacos"


def get_version() -> str:
    info_path = Path(__file__).parent / PROJECT_NAME / "__init__.py"
    with open(info_path, "rt") as info_handle:
        info = info_handle.read()
    try:
        version = (re.search(r"^__version__ = *[\"'](.+)[\"']",  # type: ignore
                             info,
                             re.MULTILINE)
                   .group(1))
    except Exception as e:
        raise RuntimeError("Failed to parse version string from {path}"
                           .format(path = info_path.as_posix()))
    return version


def get_required_packages_from_pipfile() -> List[str]:
    """Parses Pipfile to get the list of required packages (not dev-packages)."""
    pipfile_path = Path(__file__).parent / "Pipfile"
    if not pipfile_path.exists():
        return []
    config = ConfigParser()
    config.read(pipfile_path.as_posix())
    return [k if v.strip("\"'") == "*" else k + v.strip("\"'")
            for k, v in config.items("packages")]


setup(
    name = PROJECT_NAME,
    version = get_version(),
    description = "Manage Mac OS and app preferences using config files.",
    packages = [PROJECT_NAME],
    py_modules = [],
    install_requires = get_required_packages_from_pipfile(),

    # Generate entry-points (i.e. executable scripts) in the environment.
    entry_points = """
        [console_scripts]
        {name}={name}.cli:main
    """.format(name = PROJECT_NAME),
)
