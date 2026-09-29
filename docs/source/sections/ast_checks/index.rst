AST-Based C++ Checks
=====================

The text-based style checks (header guards, keyword order, license headers)
cannot express anything that depends on *meaning* — the type of a parameter,
whether a name resolves to ``std::``, what a macro expands to. For that,
``cpp_checks`` can optionally parse each file with libclang and run a set of
semantic checks over the resulting AST.

Requirements & enabling
------------------------

AST checks need the optional ``ast`` extra (bundles ``libclang``):

.. code-block:: console

   pip install devops[ast]

They are on by default once installed. Toggle and tune them from the
``[cpp]`` section:

.. list-table::
   :header-rows: 1
   :widths: 25 75

   * - Key
     - Purpose
   * - ``ast_checks``
     - Master on/off switch (default ``true``).
   * - ``ast_check_compile_commands_db``
     - Directory containing ``compile_commands.json``, for accurate per-file
       compile flags. Strongly recommended for CMake projects.
   * - ``ast_check_compile_args``
     - Fallback compiler flags (e.g. ``-std=c++23``) used when no compile
       commands database is set, or a file isn't listed in it.
   * - ``ast_check_enabled_ids`` / ``ast_check_disabled_ids``
     - Allowlist / denylist of check ids, by the ``Check id`` column below.

See :doc:`../configuration` for the full key reference, defaults, and a
worked TOML example.

How checks run
----------------

All enabled checks share a single preorder walk over each file's AST (see
``devops.cpp.ast.engine``) — adding another check never costs another parse.
Each one implements ``devops.cpp.ast.base.Check`` and reports zero or more
``Diagnostic``\ s, formatted like cppcheck output:

.. code-block:: text

   src/box.cpp:42:18: style: parameter of type 'molsys::SimulationBox' named 'box' should be named 'simulationBox' [paramNameForType]

The trailing ``[check-id]`` is what you put in ``ast_check_enabled_ids`` /
``ast_check_disabled_ids`` to select or silence that check.

Available checks
------------------

.. list-table::
   :header-rows: 1
   :widths: 20 55 25

   * - Check id
     - Flags
     - Configuration
   * - :doc:`memberLeadingUnderscore <enforce_member_leading_underscore>`
     - A private or protected member variable not starting with ``_``.
     - None
   * - :doc:`memberFunctionLeadingUnderscore <enforce_member_function_leading_underscore>`
     - A private or protected member function not starting with ``_``.
     - None
   * - :doc:`noPublicLeadingUnderscore <enforce_no_public_leading_underscore>`
     - A public member variable/function starting with ``_``.
     - None
   * - :doc:`classMemberOrder <enforce_class_member_order>`
     - A member variable/function declared before a section that must
       precede it (public/protected/private members, then
       public/protected/private member functions).
     - Optional (``excluded_macros``)
   * - :doc:`paramNameForType <param_name_for_type>`
     - A parameter of a configured type not using its canonical name.
     - Required (``type_to_name``)
   * - :doc:`macroReplacement <macro_replacement>`
     - Use of a banned macro that has a required replacement.
     - Optional (ships with a default mapping)
   * - :doc:`noGlobalUsing <no_global_using>`
     - ``using namespace X;`` / ``using X::Y;`` at global or namespace scope.
     - Optional (name filters)
   * - :doc:`noGlobalUsingEnum <no_global_using_enum>`
     - ``using enum X;`` at global or namespace scope.
     - Optional (name filters)
   * - :doc:`noThrowParen <no_throw_paren>`
     - ``throw(...)`` wrapping the whole thrown expression.
     - None

.. toctree::
   :maxdepth: 1
   :hidden:

   enforce_member_leading_underscore
   enforce_member_function_leading_underscore
   enforce_no_public_leading_underscore
   enforce_class_member_order
   param_name_for_type
   macro_replacement
   no_global_using
   no_global_using_enum
   no_throw_paren
