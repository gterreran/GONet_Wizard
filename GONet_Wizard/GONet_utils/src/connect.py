import paramiko
from typing import Callable, Any
from functools import wraps
from GONet_Wizard.GONet_utils.src.settings import config


def ssh_connect(func: Callable[[paramiko.SSHClient, Any], Any]) -> Callable[[str, Any], Any]:
    """
    A decorator for establishing an SSH connection and executing a function.

    This decorator wraps a function that requires an SSH connection, handling 
    the connection process, passing the SSH client to the wrapped function, 
    and ensuring the connection is properly closed.

    Parameters
    ----------
    func : Callable[[paramiko.client.SSHClient, Any], Any]
        A function that takes a :class:`paramiko.client.SSHClient` instance as its first argument,
        followed by any other arguments.

    Returns
    -------
    Callable[[str, Any], Any]
        A function that takes the IP address of the GONet device (`gonet_ip`), along 
        with any other arguments and keyword arguments, and returns the result of 
        the wrapped function.

    Raises
    ------
    Exception
        If the SSH connection cannot be established, an exception is raised.

    Notes
    -----
    - The function prints status messages indicating the connection and disconnection 
      process.
    - The SSH connection is established with the credentials from the `config` object.
    """

    @wraps(func)
    def wrapper(gonet_ip: str, *args: Any, **kwargs: Any) -> Any:
        # === CONNECT ===
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
            # === DISCONNECT ===
            print("🔒 Closing SSH connection.")
            ssh.close()

        return result

    return wrapper
