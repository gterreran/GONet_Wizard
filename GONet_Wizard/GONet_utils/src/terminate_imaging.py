import paramiko
from GONet_Wizard.GONet_utils.src.connect import ssh_connect

@ssh_connect
def terminate_imaging(ssh: paramiko.SSHClient) -> None:
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