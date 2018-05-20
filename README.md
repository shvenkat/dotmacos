# Manage Mac OS And App Preferences Using Config Files

Mac operating system and GUI application preferences (settings) are usually
managed using graphical interfaces, such as the System Preferences app and the
"Preferences" menu item within applications. `dotmacos` is a command-line
utility that allows you to store your preferences in human-readable config files
and apply them with a single action. You get the simplicity and transparency of
"dotfiles" across the OS and applications.


# Who Should Use `dotmacos`

  * Users who are comfortable with the terminal, and prefer simple config files
    to manage their OS and app preferences.
  * Users who track "dotfiles" for various command-line utilities in an SCM repo
    and want to do the same for MacOS and GUI apps.
  * Users who want access to settings not exposed in the GUI of the OS or apps.


# Who Shouldn't Use `dotmacos`

  * Users who are satisfied with using graphical interfaces to manually set and
    update their preferences, including on a new machine.
  * Users who are satisfied with Apple's cloud-based sync-ing of preferences.


# Installation and Use

Ensure that you have Python 2.7 or 3.6+ and git. Install with:

    pip install git+https://github.com/shvenkat/dotmacos#egg=dotmacos

This installs the Python package and a command line utility. You can now use it
as follows:

    dotmacos help
    dotmacos set  --format json5 foo.json5 [bar.json5 [...]] [--no-restart-apps]
    dotmacos get  --format json5 foo.json5 [bar.json5 [...]]
    dotmacos diff --format json5 foo.json5 [bar.json5 [...]]


# Feedback and Improvements

Comments, suggestions and contributions are welcome. Please open an issue or PR
at https://github.com/shvenkat/dotmacos.


# Engineering

## Requirements

  * Set system and GUI app preferences, which should take effect immediately and
    persist i.e. not be overwritten by the OS or apps.

  * Set preferences from human-readable config files, with string keys,
    explicitly typed values, and optional comments.

  * Save _a relevant subset_ of preferences to config files, preserving
    comments.

  * A type mismatch between old and new values for any preference key should be
    reported as a warning.

## Design

  * Use the builtin `defaults` command to get and set preferences. This is the
    recommended interface for scripts to use the MacOS preference system and
    also updates the `cfprefsd` cache. Writing plist files directly may result
    in preferences being ignored or overwritten.

  * Close apps before setting preferences to prevent apps from ignoring or
    over-writing the updated preferences. Re-start closed apps after setting
    preferences.

  * Support config files in:
      * JSON5 (explicitly typed values, comments not preserved _at present_),
      * JSON (explicitly typed values, no comments), and
      * YAML (value type inferred, comments preserved).

    See the [StrictYAML][strictyaml] project for a discussion of different
    serialization file formats, and the merits of explicit typing. Support for
    other file formats can be added easily if a parsing library is available.

    [strictyaml]: https://github.com/crdoconnor/strictyaml

  * Support single or multiple config files, to give users flexibility in
    organizing and composing their settings.

  * Do not require config file(s) to be placed in any particular location, such
    as the user's home directory.

  * Use the following UI:

        dotmacos set --format json5 foo.json5 ...
        dotmacos get --format json5 foo.json5 ...

  * Use Python for implementation. It is included on MacOS and has a plist
    library.
