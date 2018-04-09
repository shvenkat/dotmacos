% Manage MacOS Preferences Using YAML Config Files

Mac operating system and GUI application preferences (settings) are usually
managed using graphical interfaces, such as the System Preferences app and the
"Preferences" menu item within applications. `dotmacos` is a command-line
utility that allows you to store your preferences in human-readable config files
and apply them with a single action. You get the simplicity and transparency of
"dotfiles" across the OS and applications.


# Who Should Use `dotmacos`

  * Users who are comfortable with the terminal, and prefer simple config files
    over to manage their OS and app preferences.
  * Users who track dotfiles for various command-line utilities in an SCM repo
    and want to do the same for MacOS and GUI apps.


# Who Shouldn't Use `dotmacos`

  * Users who are satisfied with using graphical interfaces to manually set and
    update their preferences.
  * Users who are satisfied with Apple's cloud-based sync-ing of preferences.


# Installation and Use

Ensure that you have Python 2.7 or 3.6+ and git. Install with:

    pip install git+https://github.com/shvenkat/dotmacos#egg=dotmacos

This installs the Python package and a command line utility. You can now use it
as follows:

    dotmacos help
    dotmacos set [options] system.yaml finder.yaml safari.yaml ...
    dotmacos get [options] system.yaml finder.yaml safari.yaml ...
    dotmacos diff [options] system.yaml finder.yaml safari.yaml ...


# Feedback and Improvements

Comments, suggestions and contributions are welcome. Please open an issue or PR
at https://github.com/shvenkat/dotmacos.


# Engineering

## Requirements

  * Set system and GUI app preferences from human-readable config files.
  * Preferences set should take effect immediately and persist i.e. not be
    overwritten by the OS or apps.
  * Config files can be annotated with comments.
  * Save _a relevant subset_ of preferences to config files, preserving
    comments.

## Design

  * Use Python for implementation, as it is included in MacOS.
  * Use YAML as the config file format. Not StrictYAML (every value is a string
    and needs conversion to appropriate types). Not HJSON (not mature; python
    library does not preserve comments). Others (JSON5, HOCON) do not preserve
    comments.
  * Support single or multiple config files, each with one or more YAML
    documents, to give users flexibility in organizing and composing their
    settings.
  * Do not require config file(s) to be placed in any particular location, such
    as the user's home directory.
  * Develop as a python package with CLI -- as opposed to a single-file script -
    to ease reading and maintaining the code, and installing dependencies.
  * Use ruamel.yaml as the YAML library to preserve comments.
  * Use the builtin `defaults` command to get and set preferences. This is the
    recommended interface for scripts to use the MacOS preference system and
    also updates the `cfprefsd` cache.
  * Close apps before setting to prevent apps from ignoring or over-writing the
    updated preferences. Re-start closed apps after setting preferences.
  * Use the following UI:

        dotmacos set [--quit-apps] foo.yaml [bar.yaml [...]]
        dotmacos set [--quit-apps] <foo.yaml

        dotmacos get [--inplace] foo.yaml [bar.yaml [...]]
        dotmacos get >foo.yaml

        dotmacos diff foo.yaml [bar.yaml [...]]
