.. _user-guide-what-is-gonet-wizard:

What is GONet Wizard?
=====================

GONet Wizard is a toolkit for working with GONet image data. It provides tools
to open GONet files, inspect their metadata, visualize channels, build derived
image products, and extract measurements from selected regions of the image.

The package is called a "Wizard" because it is meant to guide common workflows
without hiding the underlying data model. Users can interact with it through a
command-line interface, a graphical launcher, or task-specific graphical tools.
In all cases, the same core processing code is used.

What GONet Wizard can do
------------------------

GONet Wizard is organized around a few broad capabilities.

Inspect images
    Display GONet files, compare channels, and generate visualization products
    for quick inspection.

Inspect metadata
    Read and display metadata associated with GONet images, including camera,
    file, time, and observing-context fields when available.

Build derived arrays
    Convert channel data into derived image-like products, such as full-array
    representations that preserve the Bayer sensor geometry.

Extract measurements
    Measure pixel statistics and metadata values from selected regions. The
    extraction system supports multiple shape types and can combine image
    measurements with metadata-derived values.

Create dashboard-ready products
    Load, merge, and visualize extracted outputs in dashboard-style workflows.

Where to go next
----------------

This User Guide introduces the input data model and the role of the package.
Task-specific documentation is organized elsewhere:

- The CLI Reference documents command syntax and command-line examples.
- The GUI Guide explains the graphical launcher and interactive windows.
- The Extraction Guide explains shapes, extractors, and extraction outputs.
- The API Reference documents the Python modules, classes, and functions.

Those sections all build on the concepts introduced here: GONet cameras, GONet
images, channels, and GONet file objects.
