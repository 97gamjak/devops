noGlobalUsing
===============

Flags ``using namespace X;`` directives and ``using X::Y;`` declarations at
global or namespace scope. The same statements inside a function, lambda, or
class body are allowed, since their effect is confined to that scope.
``using enum`` is covered by the separate :doc:`no_global_using_enum` check.

.. code-block:: cpp

   using namespace std;  // Bad — flagged, at namespace scope.

   void run() {
       using namespace std;  // Good — confined to the function body.
   }

With no configuration, every such statement is reported; the keys below
narrow that down by name. Names are matched **exactly** against the
qualified name as written in the source (``std``, ``std::literals``,
``std::string``). A leading ``::`` on an entry is ignored.

Configuration
--------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Key
     - Type
     - Default
     - Description
   * - ``enabled_names``
     - list of strings
     - ``[]``
     - If non-empty, only using-statements whose name is in this list are
       reported (allowlist).
   * - ``disabled_names``
     - list of strings
     - ``[]``
     - Using-statements whose name is in this list are never reported,
       regardless of ``enabled_names``.
   * - ``path_exceptions``
     - array of tables
     - ``[]``
     - Per-name file/directory exemptions. See below.

.. code-block:: toml

   [cpp.ast_check_config.noGlobalUsing]
   # Only complain about `using namespace std;` ...
   enabled_names = ["std"]
   # ... or, alternatively, complain about everything except these:
   # disabled_names = ["std::literals", "std::chrono_literals"]

Path exceptions
^^^^^^^^^^^^^^^

``path_exceptions`` lets you allow specific names **only in designated files or
directories**, while the rule still enforces the restriction everywhere else.
Each entry is a TOML array-of-tables element with two keys:

.. list-table::
   :header-rows: 1
   :widths: 20 15 65

   * - Key
     - Type
     - Description
   * - ``names``
     - list of strings
     - The using-statement names that are exempt in the matched paths.
       A leading ``::`` is stripped, matching the same normalisation as
       ``enabled_names`` / ``disabled_names``.
   * - ``paths``
     - list of strings
     - File-path patterns.  A pattern ending with ``/`` matches any file
       whose path **starts with** that prefix (covering all subdirectories).
       Any other pattern is matched with ``fnmatch`` (``*`` matches within a
       single directory component; ``?`` matches one character).

.. code-block:: toml

   [cpp.ast_check_config.noGlobalUsing]
   enabled_names = ["std"]

   # Allow `using rad = ...;` only inside the units/ directories
   [[cpp.ast_check_config.noGlobalUsing.path_exceptions]]
   names = ["rad"]
   paths = ["src/units/", "include/units/"]

   # Allow literals shorthands in test files only (glob pattern)
   [[cpp.ast_check_config.noGlobalUsing.path_exceptions]]
   names = ["std::literals", "std::chrono_literals"]
   paths = ["tests/*.cpp"]

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["noGlobalUsing"]
