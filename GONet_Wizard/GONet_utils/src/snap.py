import os
import paramiko
from scp import SCPClient
from GONet_Wizard.GONet_utils.src.settings import config
import hashlib


def list_remote_files(ssh, folder):
    ''' list files in a remote folder '''
    stdin, stdout, stderr = ssh.exec_command(f'ls -1 {folder}')
    return set(stdout.read().decode().splitlines())


def get_local_file_hash(filepath, algo='sha256'):
    hasher = hashlib.new(algo)
    with open(filepath, 'rb') as f:
        while chunk := f.read(8192):
            hasher.update(chunk)
    return hasher.hexdigest()


def get_remote_file_hash(ssh, remote_path, algo='sha256'):
    command = f"{algo}sum {remote_path}"
    stdin, stdout, stderr = ssh.exec_command(command)
    result = stdout.read().decode().strip()
    if stderr.read():
        return None  # File might not exist
    return result.split()[0]


def upload_if_different(ssh, local_path, remote_path):
    local_hash = get_local_file_hash(local_path)
    remote_hash = get_remote_file_hash(ssh, remote_path)

    if remote_hash is not None:
        if remote_hash == local_hash:
            print(f"✅ Remote file is identical. Skipping upload.")
            return  # No need to upload
        else:
            print(f"🆚 Remote file differs from local.")

    print(f"📤 Uploading config file: {local_path} → {remote_path}...")

    with SCPClient(ssh.get_transport()) as scp:
        scp.put(local_path, remote_path)
        print("📤 File uploaded.")
    

def run_remote_script_with_live_output(ssh, command):
    ''' live-stream stdout '''
    stdin, stdout, stderr = ssh.exec_command(command, get_pty=True)
    while not stdout.channel.exit_status_ready():
        if stdout.channel.recv_ready():
            line = stdout.channel.recv(1024).decode()
            print(line, end='')


def snap(gonet_ip:str, config_file_path:str) -> None:
    '''
    execute gonet4.py remotely, using a local config file
    
    '''
    # === CONNECT ===
    print(f"🔌 Connecting to {config.gonet_user}@{gonet_ip}...")
    ssh = paramiko.SSHClient()
    ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    try:
        ssh.connect(gonet_ip, username=config.gonet_user, password=config.gonet_password)
        print("✅ Connected successfully.")
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        exit(1)

    # === CHECK FILES BEFORE ===
    print("📂 Checking images folder before script runs...")
    initial_files = list_remote_files(ssh, config.gonet_images_folder)
    print(f"📄 Found {len(initial_files)} files before execution.")

    # === UPLOAD CONFIG FILE ===
    config_remote_file_path = os.path.join(config.gonet_config_folder, os.path.basename(config_file_path))
    upload_if_different(ssh, config_file_path, config_remote_file_path)

    # === RUN SCRIPT ===
    print("\n🚀 Running remote script with live logs...")
    cmd = f'python3 {config.gonet4_path} {config_remote_file_path}'
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
