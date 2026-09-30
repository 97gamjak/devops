noNewInGtestSetup
====================

Flags any ``new`` expression appearing anywhere inside a member function
named ``SetUp``, ``SetUpTestSuite``, or ``SetUpTestCase`` — the
fixture-setup hooks GTest calls by name. A raw pointer allocated there needs
a matching manual release, and whether that release runs depends on a
separate teardown hook firing later — see also
:doc:`noDeleteInGtestTeardown <no_delete_in_gtest_teardown>`.

.. code-block:: cpp

   class FooTest : public ::testing::Test {
   protected:
       void SetUp() override {
           ptr_ = new Foo();  // Bad — flagged.
       }

       Foo* ptr_;
   };

   class BarTest : public ::testing::Test {
   protected:
       void SetUp() override {
           ptr_ = std::make_unique<Bar>();  // Good — RAII, not flagged.
       }

       std::unique_ptr<Bar> ptr_;
   };

Only a literal ``new`` expression lexically inside the setup function's own
body is flagged — a call to some other function that itself allocates is
not traced into. A declaration with no body (e.g. a pure-virtual
``SetUp() = 0``) is never flagged, and neither is a free function of the
same name that isn't a member function.

Configuration
--------------

This check takes no configuration.

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["noNewInGtestSetup"]
