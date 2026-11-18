passByType
==========

Enforces how parameters of configured types are passed. Large types should
be taken by ``const`` reference, cheap types by value; this check keeps that
consistent across a code base.

.. code-block:: cpp

   // With "molsys::SimulationBox" = "const_ref"
   void run(molsys::SimulationBox box);          // Bad — passed by value.
   void run(molsys::SimulationBox &box);         // Bad — non-const reference.
   void run(const molsys::SimulationBox &box);   // Good.

Configuration
-------------

.. list-table::
   :header-rows: 1
   :widths: 25 15 15 45

   * - Key
     - Type
     - Default
     - Description
   * - ``types``
     - table (required)
     - —
     - Maps fully-qualified type names to a rule. A rule is either a mode
       string or a table ``{ mode = "...", check_getter = true }``.

Each rule accepts:

.. list-table::
   :header-rows: 1
   :widths: 25 15 15 45

   * - Key
     - Type
     - Default
     - Description
   * - ``mode``
     - string (required)
     - —
     - ``"const_ref"`` (must be ``const T &``), ``"value"`` (``T`` or
       ``const T``) or ``"const_ref_or_value"`` (either).
   * - ``check_getter``
     - boolean
     - ``false``
     - Also check the return type of simple getters of this type
       (non-static ``const`` member functions without parameters) against
       the same ``mode``. Other functions' return types are never checked.

Non-const lvalue references, rvalue references and pointers are always
flagged for a configured type.

Type names are matched like in :doc:`paramNameForType <param_name_for_type>`:
cv-qualifiers, references and pointers are stripped, a leading ``::`` is
ignored, and qualified names also match when wrapped in another namespace.

.. code-block:: toml

   [cpp.ast_check_config.passByType.types]
   "molsys::SimulationBox" = { mode = "const_ref", check_getter = true }
   "Real" = "value"
   "std::string_view" = { mode = "const_ref_or_value" }

The check is a no-op until ``types`` is configured.
