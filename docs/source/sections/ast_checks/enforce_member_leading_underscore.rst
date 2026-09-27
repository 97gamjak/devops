memberLeadingUnderscore
========================

Flags any non-static or static data member declared under a ``private:`` or
``protected:`` access specifier whose name doesn't start with ``_``. Public
members are never flagged.

.. code-block:: cpp

   class Widget {
   public:
       int size;      // Good — public members are not checked.

   private:
       int count;      // Bad — flagged, missing leading underscore.
       int _count;      // Good.

   protected:
       int flag;        // Bad — flagged, missing leading underscore.
       int _flag;        // Good.
   };

A member synthesized entirely by a macro invoked on that same source line
(e.g. gtest's ``TEST_F(...)`` expanding to a fixture class with its own
private ``test_info_`` member) is not flagged — there is no user-typed name
to rename.

Configuration
--------------

This check takes no configuration.

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["memberLeadingUnderscore"]
