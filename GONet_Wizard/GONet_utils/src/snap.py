import os
import paramiko
from scp import SCPClient
from GONet_Wizard.GONet_utils.src.settings import config


def list_remote_files(ssh, folder):
    ''' list files in a remote folder '''
    stdin, stdout, stderr = ssh.exec_command(f'ls -1 {folder}')
    return set(stdout.read().decode().splitlines())


def run_remote_script_with_live_output(ssh, command):
    ''' live-stream stdout '''
    stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            line = stdout.channel.recv(1024).decode()
            print(line, end='')

def snap(gonet_ip:str, config_file_name:str) -> None:
    '''
    execute gonet4.py remotely, using a local config file
    
    '''
    # === CONNECT ===
    print(f"🔌 Connecting to {config.gonet_user}@{gonet_ip}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(gonet_ip, username=config.gonet_user, password=config.remote_password)
        print("✅ Connected successfully.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        exit(1)

    # === CHECK FILES BEFORE ===
    print("📂 Checking images folder before script runs...")
    initial_files = list_remote_files(ssh, config.gonet_images_folder)
    print(f"📄 Found {len(initial_files)} files before execution.")

    # === UPLOAD CONFIG FILE ===
    print(f"📤 Uploading config file: {config_file_name} → {config.gonet_images_folder}...")
    with SCPClient(ssh.get_transport()) as scp:
        scp.put(config_file_name, os.path.join(config.gonet_images_folder, config_file_name))
    print("✅ Config file uploaded.")

    # === RUN SCRIPT ===
    print("\n🚀 Running remote script with live logs...")
    remote_config_path = os.path.join(config.gonet_images_folder, config_file_name)
    cmd = f'python3 {config.gonet4_remote_path} {remote_config_path}'
    run_remote_script_with_live_output(ssh, cmd)
    print("\n✅ Script execution finished.")

    # === CHECK FILES AFTER ===
    print("📂 Checking images folder after script runs...")
    final_files = list_remote_files(ssh, config.gonet_images_folder)
    new_files = final_files - initial_files
    print(f"🆕 New images created: {len(new_files)}")
    for f in new_files:
        print(f"   • {f}")

    # === DOWNLOAD NEW FILES ===
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

    # === DONE ===
    ssh.close()
    print("🏁 Done!")
