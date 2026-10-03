noClangFormatToggle
=====================

Flags ``// clang-format off`` / ``// clang-format on`` comments, in either
the line-comment or block-comment spelling, anywhere in the file.

.. code-block:: cpp

   // clang-format off
   int   x   =   1;   // Bad — flagged, and formatting is left inconsistent.
   // clang-format on

   /* clang-format off */  // Bad — flagged, block-comment spelling too.

These comments disable clang-format's formatting for the region they
bracket (or the rest of the file, if unbalanced), letting hand-formatted
code drift silently out of sync with the project's style over time.

Configuration
--------------

This check takes no configuration.

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["noClangFormatToggle"]
