"""
The `hood` subpackage contains the internal logic and state management used by the
GONet dashboard's interactive callbacks.

This subpackage serves as the controller layer between the frontend Dash interface
and the underlying data and visualization systems. It manages plot construction,
data filtering, selection logic, trace interactivity, and dynamic updates in
response to user input.

**Submodules**

- :mod:`.load_data` : Load and preprocess multi-epoch GONet observation data from JSON files.
- :mod:`.plot` : Plot utilities for interactive visualization of GONet sky monitoring data.

"""