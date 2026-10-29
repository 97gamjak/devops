includeIwyuPragmaOnly
=======================

Flags a trailing comment on an ``#include`` line (same line, after the
directive) that isn't an
`include-what-you-use <https://github.com/include-what-you-use/include-what-you-use>`_
pragma, i.e. doesn't match ``// IWYU pragma: <keyword> ...`` (or the
``/* ... */`` form). An ``#include`` with no trailing comment at all is
always allowed.

.. code-block:: cpp

   // Bad — flagged: not an IWYU pragma.
   #include "foo.hpp" // needed for Foo

   // Good.
   #include "foo.hpp" // IWYU pragma: keep

Restricting which pragma keywords are allowed
------------------------------------------------

By default every IWYU pragma keyword (``export``, ``keep``, ``no_include``,
``private``, ``associated``, ``friend``, ...) is accepted. Restrict the set
with ``allowed_pragmas``:

.. code-block:: toml

   [cpp.ast_check_config.includeIwyuPragmaOnly]
   allowed_pragmas = ["export", "keep"]

An IWYU pragma whose keyword isn't in the list is flagged.

Requiring a reason for specific pragmas
-------------------------------------------

Some pragma keywords can additionally be required to carry a specific
trailing reason, so the exemption is self-documenting:

.. code-block:: toml

   [cpp.ast_check_config.includeIwyuPragmaOnly]
   allowed_pragmas = ["export", "keep"]
   pragma_required_reasons = { keep = "-- for template specialization" }

.. code-block:: cpp

   // Bad — flagged: 'keep' requires a trailing reason.
   #include "foo.hpp" // IWYU pragma: keep

   // Good.
   #include "foo.hpp" // IWYU pragma: keep -- for template specialization

The required text must match exactly (after trimming surrounding
whitespace, and the closing ``*/`` for block comments). Pragma keywords not
listed in ``pragma_required_reasons`` are unaffected.

Configuration
--------------

.. list-table::
   :header-rows: 1
   :widths: 25 20 15 40

   * - Key
     - Type
     - Default
     - Description
   * - ``allowed_pragmas``
     - list of strings
     - ``[]``
     - IWYU pragma keywords that are allowed. An empty/unset list allows
       every keyword.
   * - ``pragma_required_reasons``
     - table of string to string
     - ``{}``
     - Maps a pragma keyword to the exact trailing reason text it must be
       followed by. Keywords not listed here have no reason requirement.

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["includeIwyuPragmaOnly"]
