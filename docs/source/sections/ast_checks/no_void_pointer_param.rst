noVoidPointerParam
==================

Flags ``void *`` parameters of functions that are part of a public API.
A ``void *`` erases the type and turns compile-time errors into run-time
errors, so public functions should take a typed parameter instead.

.. code-block:: cpp

   void write(const void *data);           // Bad — flagged.
   void write(std::span<const Real> data); // Good.

   class File {
     public:
       explicit File(void *handle);        // Bad — flagged.
     private:
       void _raw(void *buffer);            // Good — private.
   };

   static void cb(void *user);             // Good — internal linkage.
   namespace { void cb2(void *user); }     // Good — anonymous namespace.

A parameter is flagged when its type, after resolving typedefs and aliases
and stripping a reference, is a pointer to ``void`` at any pointer level
(``void *``, ``const void *``, ``void **``, ``void *&``, ...). This applies
to free functions and function templates with external linkage and to
public and protected member functions, member function templates and
constructors.

Never flagged:

- private member functions, ``static`` free functions, functions in an
  anonymous namespace and members of local classes,
- ``extern "C"`` declarations,
- deleted functions (``= delete``),
- methods overriding a base-class virtual method,
- function pointer parameters such as ``void (*cb)(void *)`` and parameters
  of a dependent template type such as ``T *``,
- functions and parameters whose name comes from a macro expansion.

A function is reported only at its first declaration in the translation
unit, so a method declared in a header and defined out of line in a ``.cpp``
file is reported once, in the header.

Configuration
-------------

This check takes no configuration.

Disabling
---------

.. code-block:: toml

   [cpp]
   ast_check_disabled_ids = ["noVoidPointerParam"]
