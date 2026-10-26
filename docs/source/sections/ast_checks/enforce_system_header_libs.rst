enforceSystemHeaderLibs
=========================

Flags an ``#include "lib/..."`` whose path's first directory component
matches one of the configured library names, when it should instead be
included as a system header with angle brackets. Useful for libraries whose
convention is always ``#include <lib/...>``, never a quoted include.

.. code-block:: cpp

   // Bad — flagged: 'mstd' is configured and this uses quotes.
   #include "mstd/foo.hpp"

   // Good.
   #include <mstd/foo.hpp>

Library matching
------------------

The configured library name is matched against the first path component of
the include spelling as written in the source, e.g. ``mstd`` in
``mstd/foo.hpp``. An include with no ``/`` (a bare filename) can only match
if the whole filename equals a configured library name, which is unlikely in
practice.

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
     - Library names that must always be included as system headers. An
       empty/unset list means this check never flags anything.

.. code-block:: toml

   [cpp.ast_check_config.enforceSystemHeaderLibs]
   libs = ["mstd"]

Like ``paramNameForType``, ``libs`` is required for the check to have any
effect — it is a no-op with an empty list, so it isn't meaningful to enable
without configuring it.

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["enforceSystemHeaderLibs"]
