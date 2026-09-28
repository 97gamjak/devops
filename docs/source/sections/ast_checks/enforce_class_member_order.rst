classMemberOrder
=================

Flags a member variable or member function declared before a section that
must precede it. Within a single class/struct/union body (including
templates), the direct members must appear grouped, in exactly this order:

1. public member variables
2. protected member variables
3. private member variables
4. public member functions
5. protected member functions
6. private member functions

.. code-block:: cpp

   class Widget {
   public:
       int size;

   protected:
       int flag;

   private:
       int count;

   public:
       void resize();

   protected:
       void hook();

   private:
       void compute();
   };

   class Bad {
   private:
       int count;      // Bad — flagged, a private member variable

   public:
       int size;        // before a public one.

       void resize();

   private:
       void compute();

   public:
       void hook();      // Bad — flagged, a public member function after
                          // a private one.
   };

A section may be skipped entirely (e.g. a class with no protected members
at all), but once a later section has started, an earlier one may not
reappear.

Only members declared lexically inside the class body count — an
out-of-line member-function definition (``void C::f() { ... }``) never
affects its class's ordering, only the in-class declaration does. Nested
types, ``using`` declarations, enums, friend declarations, and other
declarations not covered by the list above are ignored for ordering
purposes: they neither need to fit anywhere in particular nor reset the
sequence.

Configuration
--------------

This check takes no configuration.

Disabling
----------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["classMemberOrder"]
