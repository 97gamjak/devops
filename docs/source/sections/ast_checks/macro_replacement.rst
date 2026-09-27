macroReplacement
==================

Flags invocations of a banned macro and suggests the replacement macro that
should be used instead. Ships with a built-in default mapping and requires
no configuration to use:

.. list-table::
   :header-rows: 1
   :widths: 30 30

   * - Banned macro
     - Use instead
   * - ``EXPECT_THROW``
     - ``EXPECT_THROW_MSG``
   * - ``ASSERT_THROW``
     - ``ASSERT_THROW_MSG``

.. code-block:: cpp

   // Bad — flagged.
   EXPECT_THROW(doSomething(), std::runtime_error);

   // Good.
   EXPECT_THROW_MSG(doSomething(), std::runtime_error, "why it should throw");

Detection matches the macro name exactly (``EXPECT_THROW`` never matches
``EXPECT_THROW_MSG``) and works regardless of whether the macro is defined in
the same file or an included header (e.g. a gtest header).

Configuration
--------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Key
     - Type
     - Default
     - Description
   * - ``macro_to_replacement``
     - table of string → string
     - the built-in mapping above
     - Replaces the built-in mapping entirely when set — extend it by
       re-listing the defaults you want to keep alongside your own.

.. code-block:: toml

   [cpp.ast_check_config.macroReplacement]
   macro_to_replacement = { EXPECT_THROW = "EXPECT_THROW_MSG",
                            ASSERT_THROW = "ASSERT_THROW_MSG" }

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["macroReplacement"]
