noDeleteInGtestTeardown
=========================

Flags any ``delete``/``delete[]`` expression appearing anywhere inside a
member function named ``TearDown``, ``TearDownTestSuite``, or
``TearDownTestCase`` — the fixture-teardown hooks GTest calls by name.
Manually deleting a raw pointer there is fragile: if ``SetUp()`` throws or
returns early, the matching ``delete`` in ``TearDown()`` never runs, and if
a test body already frees the pointer, the ``TearDown()`` delete
double-frees it.

.. code-block:: cpp

   class FooTest : public ::testing::Test {
   protected:
       void TearDown() override {
           delete ptr_;  // Bad — flagged.
       }

       Foo* ptr_;
   };

   class BarTest : public ::testing::Test {
   protected:
       void TearDown() override {
           ptr_.reset();  // Good — RAII, not flagged.
       }

       std::unique_ptr<Bar> ptr_;
   };

Only a literal ``delete``/``delete[]`` lexically inside the teardown
function's own body is flagged — a call to some other function that itself
deletes something is not traced into. A declaration with no body (e.g. a
pure-virtual ``TearDown() = 0``) is never flagged, and neither is a free
function of the same name that isn't a member function.

Configuration
--------------

This check takes no configuration.

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["noDeleteInGtestTeardown"]
