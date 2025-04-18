"""
Terminate Imaging Process on a Remote GONet Device.

This script connects to a remote GONet system over SSH and forcibly terminates
any scheduled or running imaging processes. It clears the crontab, kills lingering
`gonet4.py` processes, and wipes status files from the standard status folder.

**Functions**

- :func:`terminate_imaging` : Terminate remote imaging activity and remove scheduling tasks.

"""

import paramiko
from GONet_Wizard.commands.connect import ssh_connect


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
    print("🧹 Clearing remote crontab...")
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
        print(f"⚠️ Error clearing crontab: {err.strip()}")
