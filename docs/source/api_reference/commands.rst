Command Infrastructure and Public Commands
==========================================

Command specifications, parser construction helpers, command input handling,
and top-level command modules.

Command Package
---------------

.. automodule:: GONet_Wizard.commands
   :members:
   :show-inheritance:

Specifications
--------------

.. automodule:: GONet_Wizard.commands.specs
   :members:
   :show-inheritance:

Parser Construction
-------------------

.. automodule:: GONet_Wizard.commands.parser_builder
   :members:
   :show-inheritance:

Smart Parser
------------

.. automodule:: GONet_Wizard.commands.smart_parser
   :members:
   :show-inheritance:

Argparse Errors
---------------

.. automodule:: GONet_Wizard.commands.argparse_errors
   :members:
   :show-inheritance:

CLI Core
--------

.. automodule:: GONet_Wizard.commands.cli_core
   :members:
   :show-inheritance:

Input Expansion
---------------

.. automodule:: GONet_Wizard.commands.inputs
   :members:
   :show-inheritance:

UI Bridge
---------

.. automodule:: GONet_Wizard.commands.ui_bridge
   :members:
   :show-inheritance:

Build Full Array Command
------------------------

.. automodule:: GONet_Wizard.commands.build_full_array
   :members:
   :show-inheritance:

Extract Command
---------------

.. automodule:: GONet_Wizard.commands.extract
   :members:
   :show-inheritance:

Split RAW Command
-----------------

.. automodule:: GONet_Wizard.commands.split_raw
   :members: COMMAND, output_paths_for_raw, split_raw_file, split_raw_files, cli_handler
   :exclude-members: SplitRawOutput
   :show-inheritance:

   The ``SplitRawOutput`` helper is a small return container used internally by
   the command implementation. The public API documentation focuses on the
   command specification and conversion helpers because those are the stable
   integration points.

Show Metadata Command
---------------------

.. automodule:: GONet_Wizard.commands.show_meta
   :members:
   :show-inheritance:

Dashboard Command
-----------------

.. automodule:: GONet_Wizard.commands.run_dashboard
   :members:
   :show-inheritance:

GUI Command
-----------

.. automodule:: GONet_Wizard.commands.gui
   :members:
   :show-inheritance:

Deferred Camera Commands
------------------------

The remote-camera command modules are kept in the source tree as deferred,
experimental functionality.  They are documented separately so their status is
clear and they do not get confused with the core image-processing workflow.

.. automodule:: GONet_Wizard.commands.connect
   :members:
   :show-inheritance:

.. automodule:: GONet_Wizard.commands.connect_commands
   :members:
   :show-inheritance:

.. automodule:: GONet_Wizard.commands.connect_commands.snap
   :members:
   :show-inheritance:

.. automodule:: GONet_Wizard.commands.connect_commands.terminate
   :members:
   :show-inheritance:

.. automodule:: GONet_Wizard.commands.connect_commands.ssh_utils
   :members:
   :show-inheritance:
