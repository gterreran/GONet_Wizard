.. _user-guide-introduction:

Introduction
============

GONet Wizard is a Python package for inspecting, visualizing, and extracting
measurements from images produced by GONet cameras. It provides both a command
line interface and a graphical launcher, but both interfaces are built on top of
the same underlying processing code.

The package is designed around a simple idea: GONet image files contain more
than a viewable JPEG. They also contain raw Bayer sensor data and observational
metadata that can be useful for quantitative analysis. GONet Wizard reads those
files, exposes the underlying channels, and provides tools to turn the data into
plots, tables, extracted measurements, and dashboard-ready products.

The first pages in this guide explain the data model before describing the
software interface. This order is intentional. Once the camera, image format,
channels, and :class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file.GONetFile`
objects are clear, the command-line and graphical tools become much easier to
understand.

Recommended reading order
-------------------------

If you are new to the project, start with these pages:

#. :ref:`user-guide-gonet-cameras`
#. :ref:`user-guide-gonet-images`
#. :ref:`user-guide-channels`
#. :ref:`user-guide-gonetfile`
#. :ref:`user-guide-what-is-gonet-wizard`
#. :ref:`user-guide-gui-vs-cli`
