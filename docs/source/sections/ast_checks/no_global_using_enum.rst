noGlobalUsingEnum
===================

Flags ``using enum X;`` (C++20) at global or namespace scope, where it
injects every enumerator of ``X`` into the enclosing scope. Inside a function
or class body it is allowed. This is a separate check from
:doc:`no_global_using` so the two can be enabled independently.

.. code-block:: cpp

   using enum Color;  // Bad — flagged, at namespace scope.

   void run() {
       using enum Color;  // Good — confined to the function body.
   }

It accepts the same ``enabled_names`` / ``disabled_names`` keys as
``noGlobalUsing``, matched against the qualified enum name as written (e.g.
``"molsys::HybridZone"``); a leading ``::`` is ignored.

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
     - If non-empty, only ``using enum`` declarations whose name is in this
       list are reported (allowlist).
   * - ``disabled_names``
     - list of strings
     - ``[]``
     - ``using enum`` declarations whose name is in this list are never
       reported, regardless of ``enabled_names``.

.. code-block:: toml

   [cpp.ast_check_config.noGlobalUsingEnum]
   disabled_names = ["molsys::LegacyZone"]

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["noGlobalUsingEnum"]
