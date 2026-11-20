noForbiddenInclude
===================

Flags every ``#include`` (quoted or angle-bracketed) of a library that must
never be included, in any file. A bare library name forbids the library and
all of its subfiles.

.. code-block:: cpp

   // Bad — flagged when "mp-units" is configured.
   #include <mp-units/systems/si.h>
   #include "mp-units/core.h"

Pattern matching
-----------------

Patterns are matched against the include path exactly as written in the
source. A pattern matches if it is a directory prefix (``mp-units`` matches
``mp-units/core.h`` and ``mp-units/systems/si.h``) or if it matches the whole
path as an `fnmatch` glob, where ``*`` also matches ``/`` (so
``"*_deprecated.hpp"`` and ``"boost/hana.hpp"`` work too).

Configuration
--------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Key
     - Type
     - Default
     - Description
   * - ``libs``
     - list of strings
     - ``[]``
     - Library names, directory prefixes or globs that must never be
       included. An empty/unset list means this check never flags anything.
   * - ``exclude_paths``
     - list of strings
     - ``[]``
     - Including files exempt from the check. A trailing ``/`` matches a
       directory prefix; anything else is an `fnmatch` glob.

.. code-block:: toml

   [cpp.ast_check_config.noForbiddenInclude]
   libs = ["mp-units"]
   exclude_paths = ["src/units/"]

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["noForbiddenInclude"]
