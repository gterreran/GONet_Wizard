"""
Remote Snapshot Command for GONet Devices
=========================================

This module implements the ``snap`` subcommand of the GONet Wizard CLI, enabling
remote execution of the ``gonet4.py`` imaging script on a GONet device. It
provides tools for uploading configuration files, running the script with live
output, and downloading newly created images.

The command is declared via the :data:`COMMAND` constant, a
:class:`~GONet_Wizard.commands.cli_core.CommandSpec` describing the CLI argument
structure. When parsed by the centralized CLI builder, this command is wired to
:func:`cli_handler`, which adapts the parsed :class:`argparse.Namespace` to the
core execution function :func:`take_snapshot`.

The underlying operation uses the :func:`ssh_connect` decorator from
``ssh_utils`` to automatically manage SSH connections, ensuring that each
command runs with a valid ``paramiko`` client and that the connection is safely
closed afterward.

**Functions**

- :func:`list_remote_files` : Lists files in a remote directory.
- :func:`get_local_file_hash` : Computes a hash of a local file.
- :func:`get_remote_file_hash` : Retrieves the hash of a remote file.
- :func:`upload_if_different` : Uploads a file only if it differs from the remote version.
- :func:`run_remote_script_with_live_output` : Executes a command remotely with live output streaming.
- :func:`snap` : Main entry point to execute a snapshot and transfer resulting images.
- :func:`cli_handler` : CLI handler adapting parsed arguments to the core function.

"""

import os, paramiko, hashlib, argparse
from scp import SCPClient
from GONet_Wizard.settings import GONetConfig
from GONet_Wizard.commands.connect_commands.ssh_utils import ssh_connect
from GONet_Wizard.commands.cli_core import CommandSpec

COMMAND = CommandSpec(
    name="snap",
    help="Trigger remote gonet4.py execution with optional config file.",
    args=[
        {
            "flags": ["config_file"],
            "nargs": "?",
            "default": None,
            "help": "Optional path to config file."
        }
    ]
)

def list_remote_files(ssh: paramiko.SSHClient, folder: str) -> set:
    """
    List files in a remote folder using SSH.

    Parameters
    ----------
    ssh : :class:`paramiko.client.SSHClient`
        An active SSH client connection to the remote GONet device.
    folder : :class:`str`
        Path to the remote folder to list.

    Returns
    -------
    :class:`set`
        A set of filenames found in the remote folder.
    """
    stdin, stdout, stderr = ssh.exec_command(f'ls -1 {folder}')
    return set(stdout.read().decode().splitlines())


def get_local_file_hash(filepath: str, algo: str = 'sha256') -> str:
    """
    Compute the hash of a local file.

    Parameters
    ----------
    filepath : :class:`str`
        Path to the local file.
    algo : :class:`str`, optional
        Hashing algorithm to use (default is 'sha256').

    Returns
    -------
    :class:`str`
        The computed hash as a hexadecimal string.
    """
    hasher = hashlib.new(algo)
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_remote_file_hash(ssh: paramiko.SSHClient, remote_path: str, algo: str = 'sha256') -> str | None:
    """
    Compute the hash of a remote file using SSH.

    Parameters
    ----------
    ssh : :class:`paramiko.client.SSHClient`
        An active SSH client connection.
    remote_path : :class:`str`
        Path to the remote file.
    algo : :class:`str`, optional
        Hashing algorithm (default is 'sha256').

    Returns
    -------
    :class:`str` or :class:`None`
        The remote file's hash, or None if the file does not exist or cannot be read.
    """
    command = f"{algo}sum {remote_path}"
    stdin, stdout, stderr = ssh.exec_command(command)
    result = stdout.read().decode().strip()
    if stderr.read():
        return None
    return result.split()[0]


def upload_if_different(ssh: paramiko.SSHClient, local_path: str, remote_path: str) -> None:
    """
    Upload a file only if it differs from the remote version.

    Parameters
    ----------
    ssh : :class:`paramiko.client.SSHClient`
        SSH connection to the GONet device.
    local_path : :class:`str`
        Path to the local file.
    remote_path : :class:`str`
        Destination path on the remote device.

    Returns
    -------
    None
    """
    local_hash = get_local_file_hash(local_path)
    remote_hash = get_remote_file_hash(ssh, remote_path)

    if remote_hash is not None:
        if remote_hash == local_hash:
            print(f"✅ Remote file is identical. Skipping upload.")
            return
        else:
            print(f"🆚 Remote file differs from local.")

    print(f"📤 Uploading config file: {local_path} → {remote_path}...")

    with SCPClient(ssh.get_transport()) as scp:
        scp.put(local_path, remote_path)
        print("📤 File uploaded.")


def run_remote_script_with_live_output(ssh: paramiko.SSHClient, command: str) -> None:
    """
    Run a remote command and stream stdout in real time.

    Parameters
    ----------
    ssh : :class:`paramiko.client.SSHClient`
        SSH connection to the GONet device.
    command : :class:`str`
        The command to run remotely.

    Returns
    -------
    None
    """
    stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            line = stdout.channel.recv(1024).decode()
            print(line, end='')


@ssh_connect
def take_snapshot(ssh: paramiko.SSHClient, config_file_path: str = None) -> None:
    """
    Run the GONet imaging script remotely and download new files.

    This function:
    - Checks current files in the image folder
    - Optionally uploads a config file if provided
    - Executes `gonet4.py` on the remote device
    - Downloads any newly created image files to the local machine

    Parameters
    ----------
    ssh : :class:`paramiko.client.SSHClient`
        SSH connection (automatically provided by the decorator).
    config_file_path : :class:`str`, optional
        Local path to a configuration file to be used with `gonet4.py`.

    Returns
    -------
    None

    Notes
    -----
    - Files are downloaded to the folder defined by ``LOCAL_OUTPUT_FOLDER``.
    - Requires appropriate environment variables as defined in :class:`GONet_Wizard.commands.settings.GONetConfig`.
    """
    config = GONetConfig()

    print("📂 Checking images folder before script runs...")
    initial_files = list_remote_files(ssh, config.gonet_images_folder)
    print(f"📄 Found {len(initial_files)} files before execution.")

    if config_file_path:
        config_remote_file_path = os.path.join(config.gonet_config_folder, os.path.basename(config_file_path))
        upload_if_different(ssh, config_file_path, config_remote_file_path)
    else:
        config_remote_file_path = ''

    print("\n🚀 Running remote script with live logs...")
    cmd = f'python3 {config.gonet4_path} {config_remote_file_path}'
    run_remote_script_with_live_output(ssh, cmd)
    print("\n✅ Script execution finished.")

    print("📂 Checking images folder after script runs...")
    final_files = list_remote_files(ssh, config.gonet_images_folder)
    new_files = final_files - initial_files
    print(f"🆕 New images created: {len(new_files)}")
    for f in new_files:
        print(f"   • {f}")

    if new_files:
        print(f"\n⬇️  Downloading new images to: {config.local_output_folder}")
        os.makedirs(config.local_output_folder, exist_ok=True)
        with SCPClient(ssh.get_transport()) as scp:
            for filename in new_files:
                remote_path = os.path.join(config.gonet_images_folder, filename)
                local_path = os.path.join(config.local_output_folder, filename)
                print(f"   ↳ {filename}")
                scp.get(remote_path, local_path)
        print("✅ All new images downloaded.")
    else:
        print("ℹ️ No new images to download.")

def cli_handler(args: argparse.Namespace) -> None:
    """
    CLI handler for the `snap` command.

    Parameters
    ----------
    args : :class:`argparse.Namespace`
        Parsed command-line arguments.

    Returns
    -------
    None
    
    """
    take_snapshot(args.gonet_ip, args.config_file)