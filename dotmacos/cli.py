from pathlib import Path
import sys
from typing import FrozenSet, List

import click
import click_completion

from .prefs import FileFormat, Sections


CONFIG_FORMATS: FrozenSet[str] = frozenset(FileFormat.__members__.keys())


# Initialize shell completion support.
click_completion.init()


@click.command()
def help() -> None:
    """View the manual."""
    print("""
This utility sets preferences from and saves them to structured config
files. Multiple file formats are supported, but the following structure is
required.

    <section>:
      <domain>:
        <key>: <value>

Valid sections are "user", "local" and "system" corresponding to preferences
accessed using `defaults read|write`, `defaults -currentHost read|write` and
`sudo defaults read|write` respectively.

Valid domains are those accepted by the `defaults` command. The domains
currently in use can be listed using `[sudo] defaults [-currentHost] domains`.

Valid keys and values are those used by the OS and/or applications. You can list
the keys and values currently in use for a given domain using `[sudo] defaults
[-currentHost] <domain>`. Alternatively, you can use `dotmacos get` to get the
current keys and values for all domains or for domains of your choosing.

Below is an example of a YAML config file:

    user:
      NSGlobalDomain:
        AppleLocale: en_US
        AppleLanguages:
        - en

      com.apple.finder:
        ShowPreviewPane: true

    local:
      com.apple.screensaver:
        showClock: true

    system:
      NSGlobalDomain:
        ...
""")


@click.command()
@click.option("--format", type = click.Choice(CONFIG_FORMATS), required = True,
              help = "Format of config files.")
@click.option("--no-restart-apps", is_flag = True,
              help = "Skip restarting affected applications. New preferences "
                     "may not take effect.")
@click.argument("files", type = Path, nargs = -1)
def set(format: str, no_restart_apps: bool, files: List[Path]) -> None:
    """Set OS and app preferences from config files. Restart affected
    applications to ensure that new preferences take effect immediately."""
    pass


@click.command()
@click.option("--format", type = click.Choice(CONFIG_FORMATS), required = True,
              help = "Format of config files.")
@click.option("--all-keys", is_flag = True,
              help = "Include keys not in the config files.")
@click.argument("config_paths", type = Path, nargs = -1)
def get(format: str, all_keys: bool, config_paths: List[Path]) -> None:
    """Get OS and app preferences, writing them to existing config files. Only
    keys in the config files are written, unless all_keys is True. Values are
    merged, with retrieved preferences taking precedence."""
    if len(config_paths) == 0:
        raise ValueError("Specify one or more config files.")
    file_format = FileFormat[format]
    for config_path in config_paths:
        (Sections
         .from_config_file(path = config_path, file_format = file_format)
         .merge_from_os(all_keys = all_keys)
         .to_config_file(config_path, file_format = file_format))


@click.command()
@click.option("--format", type = click.Choice(CONFIG_FORMATS), required = True,
              help = "Format of config files.")
@click.option("--all-keys", is_flag = True,
              help = "Include keys not in the config files.")
@click.argument("config_paths", type = Path, nargs = -1)
def diff(format: str, all_keys: bool, config_paths: List[Path]) -> None:
    """Show differences between current OS and app preferences, and config
    files. Only keys in the config files are used. Keys, values and value types
    are compared."""
    if len(config_paths) == 0:
        raise ValueError("Specify one or more config files.")
    file_format = FileFormat[format]
    for config_path in config_paths:
        diff_text = (
            Sections
            .from_config_file(path = config_path, file_format = file_format)
            .diff_with_os(all_keys = all_keys))
        if len(diff_text) > 0:
            print("\n" + config_path.as_posix() + ":\n")
            print("  " + diff_text.replace("\n", "\n  "))


@click.group()
def dotmacos() -> None:
    """Manage Mac OS and app preferences using config files."""
    pass


dotmacos.add_command(help)
dotmacos.add_command(set)
dotmacos.add_command(get)
dotmacos.add_command(diff)


def main() -> None:
    """This function is called by executable scripts. It calls the main CLI
    dispatcher and handles uncaught exceptions."""
    try:
        dotmacos()
    except SystemExit:  # Raised by sys.exit(), so pass it through.
        raise
    # except BaseException as e:
    #     error(status = 1, exception = e)


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
