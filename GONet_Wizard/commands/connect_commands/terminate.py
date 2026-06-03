"""
Remote Termination of Imaging Processes on a GONet Device
=========================================================

This module implements the ``terminate_imaging`` subcommand of the GONet Wizard
CLI, allowing users to remotely stop imaging activity on a GONet device. This
includes clearing scheduled tasks, killing active ``gonet4.py`` processes, and
resetting the device's status directory.

The command is declared through the :data:`COMMAND` constant, a
:class:`~GONet_Wizard.commands.cli_core.CommandSpec` describing the subcommand's
name and help text. When registered by the centralized parser builder, this
command dispatches to :func:`cli_handler`, which invokes the core remote
operation :func:`terminate_imaging`.

SSH operations are handled by the :func:`ssh_connect` decorator from
``ssh_utils``, which automatically establishes and tears down an SSH connection,
ensuring safe and consistent remote execution.

**Functions**

- :func:`terminate_imaging` : Terminate remote imaging activity and remove scheduling tasks.
- :func:`cli_handler` : CLI handler to terminate remote imaging.

"""

import paramiko, argparse
from GONet_Wizard.commands.connect_commands.ssh_utils import ssh_connect
from GONet_Wizard.commands.cli_core import CommandSpec
from GONet_Wizard.logging_utils import get_logger

logger = get_logger(__name__)

COMMAND = CommandSpec(
    name="terminate_imaging",
    help="Terminate remote gonet4.py execution and clear scheduling tasks.",
    args=[]
)

@ssh_connect
def terminate_imaging(ssh: paramiko.SSHClient) -> None:
    """
    Terminate remote imaging activity and remove scheduling tasks.

    This function connects via SSH to the remote GONet device and performs the following:
    - Clears the crontab (removing all scheduled tasks)
    - Kills any remaining `gonet4.py` processes
    - Deletes contents of `/home/pi/Tools/Status/`
    - Creates a marker file to indicate imaging is terminated and disabled

    Parameters
    ----------
    ssh : :class:`paramiko.client.SSHClient`
        An active SSH connection provided by the :func:`GONet_Wizard.commands.connect.ssh_connect` decorator.

    Returns
    -------
    None

    Notes
    -----
    - The `ssh_connect` decorator handles connection and disconnection.
    - If crontab removal or process termination fails, a warning is printed.

    """
    logger.info("Clearing remote crontab.")
    command = (
        "crontab -r && "
        "ps aux | grep '[g]onet4.py' | grep -v $$ | awk '{print $2}' | xargs -r kill && "
        "rm -rf /home/pi/Tools/Status/* && "
        "touch /home/pi/Tools/Status/TerminatedAndDisabled! && "
        "echo '✅ Cleanup complete.'"
    )
    stdin, stdout, stderr = ssh.exec_command(command)
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()

    if err:
        logger.warning("Error clearing crontab: %s", err.strip())


def cli_handler(args: argparse.Namespace) -> None:
    """
    CLI handler to terminate remote imaging.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Parsed command-line arguments containing the necessary parameters.

    Returns
    -------
    None

    """
    terminate_imaging(args.gonet_ip)