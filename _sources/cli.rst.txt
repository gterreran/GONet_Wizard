Command-Line Interface
======================

.. automodule:: GONet_Wizard.__main__

Available Commands
------------------

- **show** — Plot GONet GONet files by channel
- **show_meta** — Print metadata of files
- **dashboard** — Launch the interactive dashboard
- **connect snap** — Trigger remote snapshot
- **connect terminate_imaging** — Kill imaging processes remotely

Usage Examples
--------------

.. code-block:: bash

   GONet_Wizard show image1.npy --red
   GONet_Wizard show_meta *.npy
   GONet_Wizard dashboard
   GONet_Wizard connect 192.168.0.101 snap config.json
   GONet_Wizard connect 192.168.0.101 terminate_imaging

Submodules
__________

.. autofunction:: GONet_Wizard.__main__.main