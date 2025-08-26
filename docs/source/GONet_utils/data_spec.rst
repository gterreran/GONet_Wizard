data_spec
==========

.. automodule:: GONet_Wizard.GONet_utils.src.data_spec


Classes:
---------------

.. autoclass:: GONet_Wizard.GONet_utils.src.data_spec.Field
   :members:
   :undoc-members:
   :show-inheritance:


data_spec.yaml
--------------

The `data_spec.yaml <https://github.com/gterreran/GONet_Wizard/blob/master/GONet_Wizard/GONet_utils/src/data_spec.yaml>`_ file serves as a mapping between the hardcoded labels used in the code for extracted quantities and the user-friendly labels or aliases that the user wants to display. This ensures flexibility and customization without altering the hardcoded labels in the code.

Purpose
-------
- Allows users to change the display labels for extracted quantities (e.g., "date").
- Enables the addition of aliases for extracted quantities, providing alternative names for the same field.
- Keeps the hardcoded labels in the code unchanged, ensuring consistency and stability in the extraction pipeline.

By modifying the `data_spec.yaml <https://github.com/gterreran/GONet_Wizard/blob/master/GONet_Wizard/GONet_utils/src/data_spec.yaml>`_ file, users can customize how extracted quantities are presented in the user interface or reports, without requiring changes to the underlying code.
