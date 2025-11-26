Command-Line Interface
======================

.. automodule:: GONet_Wizard.cli

Usage Examples
--------------

.. code-block:: bash

   GONet_Wizard show image1.npy --red
   GONet_Wizard show_meta *.npy
   GONet_Wizard extract 202_*jpg --shape circle --center 1000,750 --radius 200
   GONet_Wizard dashboard
   GONet_Wizard connect 192.168.0.101 snap config.json
   GONet_Wizard connect 192.168.0.101 terminate_imaging

Functions:
----------

.. autofunction:: GONet_Wizard.__main__.main