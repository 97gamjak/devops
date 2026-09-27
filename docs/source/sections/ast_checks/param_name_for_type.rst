paramNameForType
==================

Enforces that every parameter of a configured type uses one canonical name,
e.g. every ``molsys::SimulationBox`` parameter must be called ``simulationBox``.
Useful for keeping a consistent naming convention across a large codebase.

.. code-block:: cpp

   // Bad — flagged: 'box' is not the configured name for SimulationBox.
   void run(const molsys::SimulationBox &box);

   // Good.
   void run(const molsys::SimulationBox &simulationBox);

Type matching
--------------

Configured type names are matched after stripping cv-qualifiers, references,
and pointers, so ``"const SimulationBox &"``, ``"SimulationBox *"`` and
``"SimulationBox"`` all resolve to the same key and require the same
parameter name. A leading ``::`` on a key is also stripped automatically.

Qualified keys (containing ``::``) use *suffix* matching, so
``"molsys::SimulationBox"`` also matches ``"std::molsys::SimulationBox"`` — a
known libclang/GCC quirk where some standard-library-adjacent contexts wrap
user namespaces.

Configuration
--------------

.. list-table::
   :header-rows: 1
   :widths: 20 15 15 50

   * - Key
     - Type
     - Default
     - Description
   * - ``type_to_name``
     - table (required)
     - —
     - Maps fully-qualified type names to the required parameter name, or a
       list of accepted names.
   * - ``unseen_type_is_error``
     - boolean
     - ``false``
     - If ``true``, a configured type that is never encountered as a
       parameter type across all checked files fails the run (instead of
       just logging a warning). Useful for catching typos in the
       ``type_to_name`` keys.

.. code-block:: toml

   [cpp.ast_check_config.paramNameForType]
   # Single accepted name:
   type_to_name = { "molsys::SimulationBox" = "simulationBox" }

   # Multiple accepted names:
   # type_to_name = { "molsys::SimulationBox" = ["simulationBox", "box"] }

   unseen_type_is_error = true

Unlike the other AST checks, ``type_to_name`` is required — this check is a
no-op with an empty mapping, so it isn't meaningful to enable without
configuring it.
