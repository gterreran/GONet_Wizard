callbacks
=========

.. automodule:: GONet_Wizard.GONet_dashboard.src.callbacks

Dash callbacks:
---------------

.. autofunction:: GONet_Wizard.GONet_dashboard.src.callbacks.load
.. autofunction:: GONet_Wizard.GONet_dashboard.src.callbacks.plot
.. autofunction:: GONet_Wizard.GONet_dashboard.src.callbacks.info
.. autofunction:: GONet_Wizard.GONet_dashboard.src.callbacks.activate_fold_switch
.. autofunction:: GONet_Wizard.GONet_dashboard.src.callbacks.add_filter
.. autofunction:: GONet_Wizard.GONet_dashboard.src.callbacks.add_or_filter
.. autofunction:: GONet_Wizard.GONet_dashboard.src.callbacks.update_main_filters_value
.. autofunction:: GONet_Wizard.GONet_dashboard.src.callbacks.update_secondary_filters_value
.. autofunction:: GONet_Wizard.GONet_dashboard.src.callbacks.update_filters
.. autofunction:: GONet_Wizard.GONet_dashboard.src.callbacks.export_data
.. autofunction:: GONet_Wizard.GONet_dashboard.src.callbacks.save_status
.. autofunction:: GONet_Wizard.GONet_dashboard.src.callbacks.load_status
.. autofunction:: GONet_Wizard.GONet_dashboard.src.callbacks.update_filter_selection_state
.. autofunction:: GONet_Wizard.GONet_dashboard.src.callbacks.add_selection_filter

Clientside Callback: Export Dashboard Status
--------------------------------------------

This clientside callback enables users to export the current dashboard state
as a JSON file. The data is serialized in the browser and downloaded via a
temporary Blob URL.

**Inputs**:
  - ``status-data.data``: A dictionary containing the current UI state, including axis selections, filters, and switches.

**Outputs**:
  - ``dummy-div.children``: Used solely to trigger the callback.

**Behavior**:
  - Prompts the user to enter a filename (default: ``status.json``).
  - Converts the status dictionary into a formatted JSON string.
  - Creates a Blob and object URL.
  - Initiates the download using a temporary anchor tag.
  - Cleans up all temporary DOM elements and object URLs afterward.

**Usage Notes**:
  - This approach is quick and convenient for small data payloads.
  - It uses browser-native functionality and does not require server interaction.
  - The callback is designed to be self-contained and avoids the need for backend downloads.
  - A more robust alternative using the File System Access API is commented in the code, but is currently disabled due to limited UI polish and cross-browser compatibility.

**Future Improvements**:
  - For larger payloads or enhanced control, this behavior may eventually be migrated to the Django backend.

