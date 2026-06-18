User Guide
==========

The User Guide introduces the observational and software concepts behind
GONet Wizard. It is intended for readers who want to understand what GONet
images contain, how GONet Wizard represents them internally, and how the GUI
and command-line interfaces relate to the same processing engine.

This section deliberately starts with the input domain: GONet cameras, GONet
images, channels, and the :class:`~GONet_Wizard.GONet_utils.src.gonet.gonet_file.GONetFile`
model. Task-specific documentation, such as extraction workflows, command-line
syntax, and GUI walkthroughs, is covered in the dedicated sections linked from
the main documentation index.

.. toctree::
   :maxdepth: 2

   introduction
   gonet_cameras
   gonet_images
   channels
   gonetfile
   what_is_gonet_wizard
   gui_vs_cli
