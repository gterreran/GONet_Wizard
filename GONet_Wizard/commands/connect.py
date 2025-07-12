"""
SSH Connection Utilities for GONet Remote Access.

This module defines a decorator for safely managing SSH connections to a remote GONet device.
It abstracts away the connection lifecycle, allowing decorated functions to focus solely on
their task with an active :class:`paramiko.client.SSHClient` instance.


Environment
-----------
Uses credentials from :class:`GONet_Wizard.commands.settings.GONetConfig`:

- ``GONET_USER``
- ``GONET_PASSWORD``

**Functions**

- :func:`ssh_connect` : Decorator for establishing an SSH connection before calling a remote operation.

"""

import paramiko
from typing import Callable, Any
from functools import wraps
from GONet_Wizard.settings import GONetConfig


def ssh_connect(func: Callable[[paramiko.SSHClient, Any], Any]) -> Callable[[str, Any], Any]:
    """
    Decorator for establishing an SSH connection before calling a remote operation.

    This decorator wraps a function that requires a live SSH connection. It manages:
    - Setting up the SSH client
    - Connecting to the given GONet device IP
    - Passing the connected SSH client to the decorated function
    - Automatically closing the connection afterward

    Parameters
    ----------
    func : Callable[[paramiko.client.SSHClient, Any], Any]
        A function that expects a connected SSH client as its first argument.

    Returns
    -------
    Callable[[str, Any], Any]
        A new function that takes the GONet device IP address and any additional arguments.
        The SSH connection is established using the environment-configured credentials.

    Raises
    ------
    Exception
        If the SSH connection fails for any reason (auth, network, etc.), the exception is propagated.

    Example
    -------
    >>> @ssh_connect
    ... def list_home(ssh):
    ...     _, stdout, _ = ssh.exec_command("ls ~")
    ...     print(stdout.read().decode())

    >>> list_home("192.168.1.101")

    """
    @wraps(func)
    def wrapper(gonet_ip: str, *args: Any, **kwargs: Any) -> Any:
        config = GONetConfig()
        print(f"🔌 Connecting to {config.gonet_user}@{gonet_ip}...")
        ssh = paramiko.SSHClient()
        ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            ssh.connect(gonet_ip, username=config.gonet_user, password=config.gonet_password)
            print("✅ Connected successfully.")
            result = func(ssh, *args, **kwargs)
        except Exception as e:
            print(f"❌ SSH connection error: {e}")
            raise
        finally:
            print("🔒 Closing SSH connection.")
            ssh.close()

        return result

    return wrapper
