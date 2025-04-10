import paramiko
from typing import Callable, Any
from functools import wraps
from GONet_Wizard.GONet_utils.src.settings import config


def ssh_connect(func: Callable[[paramiko.SSHClient, Any], Any]) -> Callable[[str, Any], Any]:
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
