from pathlib import Path
from string import Template
import subprocess
import sys
from typing import FrozenSet, List

import click
import click_completion

from .preflib import FileFormat, Sections


MAN_PATH = Path(__file__).parent / "man.txt"
CONFIG_FORMATS: FrozenSet[str] = frozenset(FileFormat.__members__.keys())


# Initialize shell completion support.
click_completion.init()


@click.command()
def help() -> None:
    """Show the manual."""
    if not MAN_PATH.exists():
        raise Exception("Documentation ({}) not found.".format(MAN_PATH.name))
    with open(MAN_PATH.as_posix(), "rt") as man_file:
        man_template = Template(man_file.read())
    if sys.stdout.isatty():
        man_text = man_template.safe_substitute(bold = "\033[1m",
                                                reset = "\033[0m")
        subprocess.run(["less", "-R"], input = man_text.encode())
    else:
        man_text = man_template.safe_substitute(bold = "", reset = "")
        print(man_text)


@click.command()
@click.option("--format", type = click.Choice(CONFIG_FORMATS), required = True,
              help = "Format of config files.")
@click.option("--no-restart-apps", is_flag = True,
              help = "Skip restarting affected applications. New preferences "
                     "may not take effect.")
@click.option("--dry-run", is_flag = True,
              help = "Show what settings would be added or changed.")
@click.argument("config_paths", type = Path, nargs = -1)
def set(format: str, no_restart_apps: bool, dry_run: bool,
        config_paths: List[Path]) -> None:
    """Set OS and app preferences from config files. Restart affected
    applications to ensure that new preferences take effect immediately."""
    if len(config_paths) == 0:
        raise ValueError("Specify one or more config files.")
    file_format = FileFormat[format]
    for config_path in config_paths:
        if dry_run:
            diff_text = (
                Sections
                .from_config_file(path = config_path, file_format = file_format)
                .diff_with_os(os_is_base = True))
            if len(diff_text) > 0:
                print("\n" + config_path.as_posix() + ":")
                print("  " + diff_text.replace("\n", "\n  "))
        else:
            (Sections
             .from_config_file(path = config_path, file_format = file_format)
             .merge_to_os())


@click.command()
@click.option("--format", type = click.Choice(CONFIG_FORMATS), required = True,
              help = "Format of config files.")
@click.option("--all-keys", is_flag = True,
              help = "Include keys not in the config files.")
@click.option("--dry-run", is_flag = True,
              help = "Show what settings would be added or changed.")
@click.argument("config_paths", type = Path, nargs = -1)
def get(format: str, all_keys: bool, dry_run: bool, config_paths: List[Path],
        ) -> None:
    """Get OS and app preferences, writing them to existing config files. Only
    keys in the config files are written, unless all_keys is True. Values are
    merged, with retrieved preferences taking precedence."""
    if len(config_paths) == 0:
        raise ValueError("Specify one or more config files.")
    file_format = FileFormat[format]
    for config_path in config_paths:
        if dry_run:
            diff_text = (
                Sections
                .from_config_file(path = config_path, file_format = file_format)
                .diff_with_os(os_is_base = False, all_keys = all_keys))
            if len(diff_text) > 0:
                print("\n" + config_path.as_posix() + ":")
                print("  " + diff_text.replace("\n", "\n  "))
        else:
            (Sections
             .from_config_file(path = config_path, file_format = file_format)
             .merge_from_os(all_keys = all_keys)
             .to_config_file(config_path, file_format = file_format))


@click.group()
def dotmacos() -> None:
    """Manage Mac OS and app preferences using config files."""
    pass


dotmacos.add_command(help)
dotmacos.add_command(set)
dotmacos.add_command(get)


def main() -> None:
    """This function is called by executable scripts. It calls the main CLI
    dispatcher and handles uncaught exceptions."""
    try:
        dotmacos()
    except SystemExit:  # Raised by sys.exit(), so pass it through.
        raise
    except BaseException as e:
        error(status = 1, exception = e)


def error(status: int, message: str = "",
          exception: BaseException = Exception()) -> None:
    """Print a formatted message and/or exception to stderr and exit."""
    text = "\n".join([message.strip(), str(exception).strip()]).strip()
    if len(text) > 0:
        sys.stderr.write("{marker}{text}\n".format(
            marker = "\033[31mE\033[0m " if sys.stderr.isatty() else "E ",
            text = text.replace("\n", "\n  ")))
    sys.exit(status)


def info(message: str) -> None:
    """Print a formatted message to stderr."""
    if len(message) > 0:
        sys.stderr.write("{marker}{text}\n".format(
            marker = "  ",
            text = message.strip().replace("\n", "\n  ")))


if __name__ == "__main__":
    main()
