Overview
========

``devops`` is a collection of small, focused command line tools used to keep
C++ projects consistent: style and license checks on C++ sources, changelog
maintenance, and Git tag/version helpers. All tools read shared settings from
a single :doc:`configuration file <configuration>` (``devops.toml`` or
``.devops.toml``), so behavior can be tuned once and reused across every
command and CI job.

Feature areas
-------------

C++ code quality checks
^^^^^^^^^^^^^^^^^^^^^^^^

The ``cpp`` subsystem builds a set of rules from the ``[cpp]`` configuration
and runs them against a project's C++ sources:

- **Header guards** — every ``.h``, ``.hpp``, ``.tpp`` and ``.impl.hpp`` file
  must contain a proper ``#ifndef`` / ``#define`` / ``#endif`` guard. If
  ``header_guards_according_to_filepath`` is enabled, the guard macro name is
  also checked against a name derived from the file's path.
- **Key sequence order** — flags keyword sequences such as
  ``static inline constexpr`` that are written out of the expected order.
- **License headers** — verifies that source and header files start with the
  contents of a configured license header file (see below).
- **AST-based checks** (optional, requires ``pip install devops[ast]``) — uses
  libclang to parse each file and run semantic checks that text-based rules
  cannot express:

  - ``paramNameForType`` — enforces that parameters of configured types use a
    canonical name (e.g. every ``SimulationBox`` parameter must be called
    ``simulationBox``). The type-to-name mapping is configured in
    ``[cpp.ast_check_config.paramNameForType]``. Supports fully-qualified type
    names, multiple accepted names per type, and per-file compile flags from a
    ``compile_commands.json`` database.

Run it with :ref:`cpp_checks <cli-cpp_checks>`.

.. _incremental-checks:

Incremental checks
^^^^^^^^^^^^^^^^^^

For large codebases, running every check on every file on every commit can be
slow. Incremental mode skips files that have not changed since they last
passed:

- After each run, per-file results (pass/fail) and file modification times are
  persisted to a JSON state file.
- On the next run, files that passed and whose ``mtime`` is unchanged are
  skipped entirely.
- Files that failed, were modified, or are new are always re-checked.
- By default ``cpp_checks`` still stops at the first failure (**fail-fast**),
  even in incremental mode. Set ``fail_fast = false`` in ``[cpp]`` (or pass
  ``--no-fail-fast``) to check every file in one pass and record all results.

**Enable via TOML** (recommended for CI / permanent projects):

.. code-block:: toml

   [cpp]
   incremental_state_file = "build/.cpp_check_state.json"
   # Optional: disable fail-fast to record results for all files in one pass
   # fail_fast = false

Add the state file to ``.gitignore`` — it is machine-local and should not be
committed.

**Enable via CLI** (one-off or scripting):

.. code-block:: console

   cpp_checks --incremental
   cpp_checks --incremental --state-file build/.cpp_check_state.json
   cpp_checks --incremental --no-fail-fast   # check all files, save full state

``--state-file`` implies ``--incremental`` and takes precedence over the TOML
setting. When ``--incremental`` is used without ``--state-file``, the TOML
path is used if configured; otherwise the default path
(``.devops_cpp_state.json`` in the current directory) is used.

License header management
^^^^^^^^^^^^^^^^^^^^^^^^^^

Beyond just checking for a license header, ``devops`` can insert one into
files that are missing it, one file at a time or recursively across
directories. See :ref:`add_license_header <cli-add_license_header>` and
:ref:`add_license_headers <cli-add_license_headers>`.

Buggy file filtering
^^^^^^^^^^^^^^^^^^^^^

Some C++ codebases need to work around known compiler bugs tied to specific
macros. :ref:`filter_buggy_cpp_files <cli-filter_buggy_cpp_files>` scans a
directory tree and prints only the files that do *not* use any macro listed
under ``exclude.buggy_cpp_macros`` — useful for scoping a workaround or a
build flag to the files that actually need it.

Changelog management
^^^^^^^^^^^^^^^^^^^^^

``devops`` maintains ``CHANGELOG.md`` files with a simple insertion-marker
convention: a ``## Next Release`` heading followed by an
``<!-- insertion marker -->`` comment. Running
:ref:`update_changelog <cli-update_changelog>` inserts a new
``## [VERSION](.../releases/tag/VERSION) - YYYY-MM-DD`` entry right above the
marker and moves the marker down, ready for the next release.
:ref:`update_changelogs <cli-update_changelogs>` applies the same update to
every path configured under ``file.changelog_paths`` at once, which is how
this project keeps multiple changelogs (if any) in sync from a single CI
step.

Git tag utilities
^^^^^^^^^^^^^^^^^^

:ref:`get_latest_tag <cli-get_latest_tag>` and
:ref:`increase_latest_tag <cli-increase_latest_tag>` parse Git tags as
``<prefix><major>.<minor>.<patch>`` and let CI compute the next release
version without hand-maintaining it — this is what this project's own
release workflow uses to bump versions on ``hotfix/*`` branches.

CLI command reference
----------------------

All commands are installed as console scripts and read defaults from the
:doc:`configuration file <configuration>` unless overridden on the command
line.

.. _cli-cpp_checks:

``cpp_checks``
^^^^^^^^^^^^^^

Run the configured C++ style, header guard, and license header checks.
Exits with status ``1`` if any check fails.

.. code-block:: console

   cpp_checks --dirs src include
   cpp_checks --license-header LICENSE_HEADER.txt

.. _cli-add_license_header:

``add_license_header``
^^^^^^^^^^^^^^^^^^^^^^^

Prepend a license header to a single file if it doesn't already have one.

.. code-block:: console

   add_license_header src/main.cpp LICENSE_HEADER.txt
   add_license_header src/main.cpp LICENSE_HEADER.txt --dry-run

.. _cli-add_license_headers:

``add_license_headers``
^^^^^^^^^^^^^^^^^^^^^^^^

Prepend a license header to every C++ file found under the given
directories (current directory if omitted).

.. code-block:: console

   add_license_headers LICENSE_HEADER.txt --dirs src include

.. _cli-filter_buggy_cpp_files:

``filter_buggy_cpp_files``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Print the C++ files under the given directories that do **not** contain any
macro listed in ``exclude.buggy_cpp_macros``.

.. code-block:: console

   filter_buggy_cpp_files --dirs src include

.. _cli-update_changelog:

``update_changelog``
^^^^^^^^^^^^^^^^^^^^^

Insert a new version entry into one changelog file.

.. code-block:: console

   update_changelog 1.2.0
   update_changelog 1.2.0 --changelog-path docs/CHANGELOG.md

.. _cli-update_changelogs:

``update_changelogs``
^^^^^^^^^^^^^^^^^^^^^^

Insert a new version entry into every changelog configured under
``file.changelog_paths`` (or a custom set passed explicitly).

.. code-block:: console

   update_changelogs 1.2.0
   update_changelogs 1.2.0 --changelog-paths CHANGELOG.md docs/CHANGELOG.md

.. _cli-get_latest_tag:

``get_latest_tag``
^^^^^^^^^^^^^^^^^^^

Print the latest Git tag, parsed as ``<prefix><major>.<minor>.<patch>``.

.. code-block:: console

   get_latest_tag
   get_latest_tag --prefix v

.. _cli-increase_latest_tag:

``increase_latest_tag``
^^^^^^^^^^^^^^^^^^^^^^^^

Print the next version after bumping the latest Git tag. Exactly one of
``--major``, ``--minor``, or ``--patch`` must be given.

.. code-block:: console

   increase_latest_tag --patch
   increase_latest_tag --major --prefix v

``generate_toml_template``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Write ``devops.toml.template`` to the current directory: every configuration
key, commented out, set to its default value. See
:doc:`configuration` for what each key does.

.. code-block:: console

   generate_toml_template
