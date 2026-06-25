"""
Dash-based GUI for extracting regions from GONet images.

This subpackage defines the interactive graphical user interface (GUI) for
selecting and analyzing regions in GONet camera images. It provides a full Dash
application for loading images, choosing shapes (circle, rectangle, annulus, or
freehand), and extracting summary statistics from selected regions.

The GUI is launched via the `run_extraction_gui()` function, which is designed
to be called from a CLI command or programmatically.

***Submodules***

- :mod:`.extract_server` : Defines the Flask server and `Dash <https://dash.plotly.com/>`_ app instance used by the GONet extraction GUI.
- :mod:`.extract_gui` : Entry point for launching the GONet extraction GUI.
- :mod:`.extract_layout` : Defines the Dash layout for the GONet extraction GUI.
- :mod:`.extract_callbacks` : Defines the core interactivity for the GONet extraction GUI via Dash callbacks.
- :mod:`.shapes` : Provides functions to generate Plotly-compatible shape dictionaries.

"""