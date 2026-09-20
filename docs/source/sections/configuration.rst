Configuration File
===================

Every ``devops`` command reads its defaults from a single TOML configuration
file. This page is the complete reference for that file: where it's
discovered, every section and key it supports, and the exact defaults used
when a key (or the whole file) is missing.

Discovery
---------

On startup, ``devops`` looks in the **current working directory** for:

#. ``devops.toml``
#. ``.devops.toml``

- If exactly **one** of these files exists, it is loaded and parsed.
- If **neither** exists, the built-in defaults documented below are used.
- If **both** exist, a warning is logged and the built-in defaults are used
  — the ambiguity is intentionally not resolved automatically.

There is no parent-directory search: the file must sit in the directory the
command is run from.

Generating a starting point
----------------------------

Rather than writing the file by hand, run:

.. code-block:: console

   generate_toml_template

This writes ``devops.toml.template`` in the current directory containing
every key below, commented out, set to its default value. Rename it to
``devops.toml`` (or ``.devops.toml``) and uncomment/edit what you need to
override.

Reference
---------

Keys are optional unless stated otherwise — anything omitted falls back to
its default.

``[exclude]``
^^^^^^^^^^^^^

Controls which files are excluded from checks.

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Key
     - Type
     - Default
     - Description
   * - ``buggy_cpp_macros``
     - list of strings
     - ``[]``
     - Macro names that mark a file as affected by a known compiler bug.
       :ref:`filter_buggy_cpp_files <cli-filter_buggy_cpp_files>` excludes
       any file that calls one of these macros (matched as a whole word
       immediately followed by ``(``).

.. code-block:: toml

   [exclude]
   buggy_cpp_macros = ["MACRO_A", "MACRO_B"]

``[logging]``
^^^^^^^^^^^^^

Per-subsystem log levels. Valid values: ``NONE``, ``DEBUG``, ``INFO``,
``WARNING``, ``ERROR``, ``CRITICAL``.

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Key
     - Type
     - Default
     - Description
   * - ``global_level``
     - string
     - ``"INFO"``
     - Root logger level.
   * - ``utils_level``
     - string
     - ``"INFO"``
     - Level for the ``utils`` subsystem.
   * - ``config_level``
     - string
     - ``"INFO"``
     - Level for the configuration-loading subsystem itself.
   * - ``cpp_level``
     - string
     - ``"INFO"``
     - Level for the C++ checks subsystem.

.. code-block:: toml

   [logging]
   global_level = "INFO"
   cpp_level = "DEBUG"

``[git]``
^^^^^^^^^

Controls how Git tags are parsed by
:ref:`get_latest_tag <cli-get_latest_tag>` and
:ref:`increase_latest_tag <cli-increase_latest_tag>`.

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Key
     - Type
     - Default
     - Description
   * - ``tag_prefix``
     - string
     - ``""``
     - Prefix expected before the ``major.minor.patch`` part of a tag (for
       example ``"v"`` for tags like ``v1.2.3``). Tags without this prefix
       are ignored when finding the latest tag.
   * - ``empty_tag_list_allowed``
     - boolean
     - ``true``
     - If ``true`` and no matching tags exist, the latest tag is treated as
       ``<prefix>0.0.0`` instead of raising an error.

.. code-block:: toml

   [git]
   tag_prefix = "v"
   empty_tag_list_allowed = true

``[cpp]``
^^^^^^^^^

Controls the checks run by :ref:`cpp_checks <cli-cpp_checks>`.

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Key
     - Type
     - Default
     - Description
   * - ``style_checks``
     - boolean
     - ``true``
     - Enable header guard presence checks and keyword-order checks (e.g.
       ``static inline constexpr``).
   * - ``license_header_check``
     - boolean
     - ``true``
     - Enable verifying that files start with the configured license
       header. Has no effect if ``license_header`` is not set.
   * - ``license_header``
     - string or unset
     - unset
     - Path to a file whose contents must appear at the top of every C++
       source/header file. Required for ``license_header_check`` to do
       anything.
   * - ``check_only_staged_files``
     - boolean
     - ``false``
     - Restrict checks to files currently staged in Git (for pre-commit
       hook usage).
       The ``--base-ref`` CLI option overrides this setting. See
       :ref:`changed-files checks <changed-files-checks>`.
   * - ``check_dirs``
     - list of strings
     - ``[]``
     - If non-empty, only files under these directories (relative to the
       current working directory, glob patterns supported) are checked.
       Ignored when ``check_only_staged_files`` is ``true`` or when
       ``--base-ref`` is given.
   * - ``exclude_dirs``
     - list of strings
     - ``[]``
     - Directory names to skip during recursive scanning, regardless of
       whether ``check_dirs`` is set (e.g. ``["build", ".git"]``).
   * - ``header_guards_according_to_filepath``
     - boolean
     - ``false``
     - Additionally require the header guard macro name to match a name
       derived from the file's path, not just be present.
   * - ``ast_checks``
     - boolean
     - ``true``
     - Enable libclang AST-based checks (see below). Requires the optional
       ``ast`` extra: ``pip install devops[ast]``.
   * - ``ast_check_compile_args``
     - list of strings
     - ``["-std=c++23"]``
     - Compiler flags passed to libclang when parsing files for AST checks
       (e.g. C++ standard, include paths). Used as a fallback when
       ``ast_check_compile_commands_db`` is not set or a file is not in
       the database.
   * - ``ast_check_compile_commands_db``
     - string or unset
     - unset
     - Path to the directory containing ``compile_commands.json`` (e.g.
       ``"build"`` or ``".build"``). When set, per-file compile flags are
       read from the database; falls back to ``ast_check_compile_args``
       for unlisted files. Strongly recommended for projects built with
       CMake — without it, header includes may be missing and some files
       may fail to parse.
   * - ``ast_check_enabled_ids``
     - list of strings
     - ``[]``
     - If non-empty, only AST checks whose ``id`` is in this list run
       (allowlist). See available check ids below.
   * - ``ast_check_disabled_ids``
     - list of strings
     - ``[]``
     - AST checks whose ``id`` is in this list are always skipped,
       regardless of ``ast_check_enabled_ids``.
   * - ``incremental_state_file``
     - string or unset
     - unset
     - Path to a JSON file used to persist per-file check results between
       runs. When set, ``cpp_checks`` runs in *incremental* mode
       automatically: only files that are new, previously failed, or
       modified since the last run are re-checked. Already-passing,
       unchanged files are skipped. The file is created on the first run
       and updated after every subsequent run. The ``--incremental`` CLI
       flag can enable the same mode without touching the config; when
       ``--state-file`` is also given it takes precedence over this
       setting. See :ref:`incremental checks <incremental-checks>`.
   * - ``fail_fast``
     - boolean
     - ``true``
     - When ``true`` (the default), ``cpp_checks`` stops at the first file
       that fails and reports an error. Set to ``false`` to check all files
       regardless of failures — useful in incremental mode (together with
       ``incremental_state_file``) to get a complete picture of the
       codebase in a single pass. Can also be overridden at runtime with
       the ``--no-fail-fast`` CLI flag.

.. code-block:: toml

   [cpp]
   style_checks = true
   license_header_check = true
   license_header = "LICENSE_HEADER.txt"
   check_only_staged_files = false
   check_dirs = ["src", "include", "tests"]
   exclude_dirs = ["build", ".build"]
   header_guards_according_to_filepath = true
   ast_checks = true
   ast_check_compile_commands_db = ".build"
   incremental_state_file = "build/.cpp_check_state.json"
   fail_fast = false

``[cpp.ast_check_config.<check-id>]``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Per-check configuration lives in sub-tables of ``[cpp.ast_check_config]``,
one sub-table per check id. Each check defines its own keys; unknown keys are
silently ignored.

.. rubric:: ``paramNameForType``

Enforces that parameters of specific types use a canonical name. Useful for
keeping a consistent naming convention across a large codebase (e.g. every
``SimulationBox`` parameter should be called ``simulationBox``).

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Key
     - Type
     - Default
     - Description
   * - ``type_to_name``
     - table (required)
     - —
     - Maps fully-qualified type names to the required parameter name (or
       a list of accepted names). Keys are matched after stripping
       cv-qualifiers, references, and pointers, so ``"const Foo &"`` and
       ``"Foo *"`` both resolve to ``"Foo"``.  A leading ``::`` on a key
       is also stripped automatically.  Qualified keys (containing ``:``)
       use suffix matching, so ``"molsys::Foo"`` also matches
       ``"std::molsys::Foo"`` (a known libclang/GCC quirk).
   * - ``unseen_type_is_error``
     - boolean
     - ``false``
     - If ``true``, a configured type that was never encountered as a
       parameter type across all checked files causes the run to fail
       (instead of just logging a warning). Useful for catching typos in
       the ``type_to_name`` keys.

.. code-block:: toml

   [cpp.ast_check_config.paramNameForType]
   # Single accepted name:
   type_to_name = { "molsys::SimulationBox" = "simulationBox" }

   # Multiple accepted names:
   # type_to_name = { "molsys::SimulationBox" = ["simulationBox", "box"] }

   unseen_type_is_error = true

``[file]``
^^^^^^^^^^

Controls changelog file handling and text encoding.

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Key
     - Type
     - Default
     - Description
   * - ``encoding``
     - string
     - ``"utf-8"``
     - Encoding used to read/write changelog files. Must be a valid Python
       codec name; an invalid value fails config loading immediately.
   * - ``changelog_paths``
     - string or list of strings
     - ``["CHANGELOG.md"]``
     - The changelog file(s) managed by
       :ref:`update_changelogs <cli-update_changelogs>`. A single string is
       accepted and treated as a one-element list.
   * - ``default_changelog_path``
     - string or unset
     - first entry of ``changelog_paths``
     - Which changelog :ref:`update_changelog <cli-update_changelog>` writes
       to when ``--changelog-path`` isn't given on the command line.

.. code-block:: toml

   [file]
   encoding = "utf-8"
   changelog_paths = ["CHANGELOG.md"]
   default_changelog_path = "CHANGELOG.md"

Full example
------------

.. code-block:: toml

   [exclude]
   buggy_cpp_macros = ["OLD_COMPILER_WORKAROUND"]

   [logging]
   global_level = "INFO"
   cpp_level = "DEBUG"

   [git]
   tag_prefix = "v"
   empty_tag_list_allowed = true

   [cpp]
   style_checks = true
   license_header_check = true
   license_header = "LICENSE_HEADER.txt"
   header_guards_according_to_filepath = true
   check_dirs = ["src", "include", "tests"]
   ast_checks = true
   ast_check_compile_commands_db = ".build"

   [cpp.ast_check_config.paramNameForType]
   type_to_name = { "molsys::SimulationBox" = "simulationBox" }
   unseen_type_is_error = true

   [file]
   encoding = "utf-8"
   changelog_paths = ["CHANGELOG.md"]

Changelog file format
----------------------

The ``[file]`` section governs *which* changelog files are managed, but the
changelog itself has one structural requirement:
:ref:`update_changelog <cli-update_changelog>` and
:ref:`update_changelogs <cli-update_changelogs>` need a ``## Next Release``
heading followed by an ``<!-- insertion marker -->`` comment. A new entry is
inserted directly below the heading and above the marker on every run:

.. code-block:: markdown

   # Changelog

   ## Next Release

   <!-- insertion marker -->
   ## [0.1.4](https://github.com/OWNER/REPO/releases/tag/0.1.4) - 2026-09-13

   ...
