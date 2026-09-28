memberFunctionLeadingUnderscore
=================================

Flags any ordinary member function (including static and template member
functions) declared under a ``private:`` or ``protected:`` access specifier
whose name doesn't start with ``_``. Public member functions are never
flagged.

.. code-block:: cpp

   class Widget {
   public:
       void resize();     // Good — public methods are not checked.

   private:
       void compute();     // Bad — flagged, missing leading underscore.
       void _compute();     // Good.

   protected:
       void hook();         // Bad — flagged, missing leading underscore.
       void _hook();         // Good.
   };

A handful of member-function kinds are never flagged, because their name is
fixed by the language or by a base class and renaming them isn't something
the author can freely do:

- Constructors and destructors — their name is always the class's own name
  (or ``~ClassName``).
- Operator overloads and conversion functions (``operator==``,
  ``operator[]``, ``operator int() const``, ...) — the operator's spelling
  is fixed by the language grammar.
- Methods that override a base class's virtual method — the override must
  keep the base method's exact name to bind at all.

As with :doc:`memberLeadingUnderscore <enforce_member_leading_underscore>`,
a member function synthesized entirely by a macro invoked on that same
source line is not flagged either — there is no user-typed name to rename.

Configuration
--------------

This check takes no configuration.

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["memberFunctionLeadingUnderscore"]
