enforceCppOnlyInclude
=========================

Flags an ``#include`` of a configured header found inside another header
file. Useful for headers that are implementation details of a single
translation unit (e.g. a ``*_impl.hpp`` meant to be included at the bottom
of exactly one ``.cpp``) and must never leak into other headers.

.. code-block:: cpp

   // other.hpp
   // Bad — flagged: 'detail/foo_impl.hpp' is configured and this is a header.
   #include "detail/foo_impl.hpp"

   // foo.cpp
   // Good — including it directly from a .cpp file is always allowed.
   #include "detail/foo_impl.hpp"

Header matching
------------------

Each configured pattern is matched with `fnmatch` rules (``*`` matches
within a path component) against the ``#include`` path exactly as written
in the source, and against its basename — so both a full relative path
(``detail/foo_impl.hpp``) and a bare glob (``*_internal.hpp``) work.

Configuration
--------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Key
     - Type
     - Default
     - Description
   * - ``headers``
     - list of strings
     - ``[]``
     - Patterns identifying headers that may only be included from ``.cpp``
       files. An empty/unset list means this check never flags anything.

.. code-block:: toml

   [cpp.ast_check_config.enforceCppOnlyInclude]
   headers = ["detail/foo_impl.hpp", "*_internal.hpp"]

Like ``paramNameForType``, ``headers`` is required for the check to have
any effect — it is a no-op with an empty list, so it isn't meaningful to
enable without configuring it.

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["enforceCppOnlyInclude"]
