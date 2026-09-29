noPublicLeadingUnderscore
===========================

Flags any data member or member function declared under a ``public:``
access specifier (or under no access specifier at all in a
``struct``/``union``) whose name starts with ``_``. Private/protected
members are never flagged here — that's the concern of
:doc:`memberLeadingUnderscore <enforce_member_leading_underscore>` and
:doc:`memberFunctionLeadingUnderscore
<enforce_member_function_leading_underscore>`.

.. code-block:: cpp

   class Widget {
   public:
       int size;        // Good.
       int _size;        // Bad — flagged, leading underscore on a public member.

       void compute();  // Good.
       void _compute();  // Bad — flagged, leading underscore on a public method.

   private:
       int _count;        // Good — not checked here.
   };

Constructors/destructors, operator overloads/conversions, and methods
overriding a base-class virtual method are always exempt, since their names
aren't the author's to change. A member synthesized entirely by a macro
invoked on that same source line is not flagged either — there is no
user-typed name to rename.

Configuration
--------------

This check takes no configuration.

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["noPublicLeadingUnderscore"]
