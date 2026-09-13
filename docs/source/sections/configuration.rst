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
   * - ``header_guards_according_to_filepath``
     - boolean
     - ``false``
     - Additionally require the header guard macro name to match a name
       derived from the file's path, not just be present.

.. code-block:: toml

   [cpp]
   style_checks = true
   license_header_check = true
   license_header = "LICENSE_HEADER.txt"
   check_only_staged_files = false
   header_guards_according_to_filepath = true

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
