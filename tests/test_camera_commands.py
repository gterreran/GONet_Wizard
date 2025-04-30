import pytest, os, sys
from unittest.mock import patch, MagicMock
from GONet_Wizard.commands.connect import ssh_connect
from GONet_Wizard.commands.settings import GONetConfig

import GONet_Wizard.commands.snap as snap
from GONet_Wizard.commands import terminate

from GONet_Wizard.commands.settings import require_env_var
from GONet_Wizard.commands.settings import DashboardConfig

def test_ssh_connect_success():
    mock_ssh = MagicMock()

    @ssh_connect
    def fake_remote_op(ssh):
        return ssh.do_something()

    with patch("GONet_Wizard.commands.connect.paramiko.SSHClient", return_value=mock_ssh):
        with patch("GONet_Wizard.commands.connect.GONetConfig") as mock_config:
            mock_config.return_value.gonet_user = "user"
            mock_config.return_value.gonet_password = "pass"
            mock_ssh.exec_command.return_value = (None, MagicMock(), None)
            mock_ssh.do_something.return_value = "called"

            result = fake_remote_op("192.168.1.10")
            assert result == "called"
            mock_ssh.connect.assert_called_once_with("192.168.1.10", username="user", password="pass")
            mock_ssh.close.assert_called_once()


def test_ssh_connect_failure(monkeypatch):
    # Ensure GONET_USER and GONET_PASSWORD are set
    monkeypatch.setenv("GONET_USER", "pi")
    monkeypatch.setenv("GONET_PASSWORD", "whatever")

    with patch("GONet_Wizard.commands.connect.paramiko.SSHClient") as mock_ssh_class:
        mock_ssh = MagicMock()
        mock_ssh.connect.side_effect = Exception("fail!")
        mock_ssh_class.return_value = mock_ssh

        @ssh_connect
        def dummy(_ssh): ...

        with pytest.raises(Exception, match="fail!"):
            dummy("192.168.1.10")

        mock_ssh.close.assert_called_once()

def test_config_reads_from_env(monkeypatch):
    monkeypatch.setenv("GONET_USER", "admin")
    monkeypatch.setenv("GONET_PASSWORD", "secret")

    config = GONetConfig()
    assert config.gonet_user == "admin"
    assert config.gonet_password == "secret"


def test_config_prompts_for_password(monkeypatch):
    monkeypatch.delenv("GONET_PASSWORD", raising=False)
    monkeypatch.setenv("GONET_USER", "admin")

    with patch("builtins.input", return_value="typed_pw"):
        config = GONetConfig()
        assert config.gonet_password == "typed_pw"

def test_require_env_var_returns_env(monkeypatch):
    monkeypatch.setenv("MY_VAR", "hello")
    from GONet_Wizard.commands.settings import require_env_var
    assert require_env_var("MY_VAR") == "hello"

def test_warn_env_var_returns_if_present(monkeypatch):
    monkeypatch.setenv("OPTIONAL_VAR", "yes")
    from GONet_Wizard.commands.settings import warn_env_var_missing
    assert warn_env_var_missing("OPTIONAL_VAR") == "yes"

def test_warn_env_var_sets_value(monkeypatch):
    monkeypatch.delenv("OPTIONAL_VAR", raising=False)
    with patch("builtins.input", side_effect=["y", "new_path"]):
        from GONet_Wizard.commands.settings import warn_env_var_missing
        result = warn_env_var_missing("OPTIONAL_VAR")
        assert result == "new_path"
        assert os.environ["OPTIONAL_VAR"] == "new_path"

def test_warn_env_var_skips(monkeypatch):
    monkeypatch.delenv("OPTIONAL_VAR", raising=False)
    with patch("builtins.input", return_value="n"):
        from GONet_Wizard.commands.settings import warn_env_var_missing
        assert warn_env_var_missing("OPTIONAL_VAR") is None


@pytest.fixture
def fake_ssh():
    mock_ssh = MagicMock()
    mock_transport = MagicMock()
    mock_ssh.get_transport.return_value = mock_transport
    return mock_ssh


def test_list_remote_files(fake_ssh):
    fake_ssh.exec_command.return_value = (None, MagicMock(read=MagicMock(return_value=b"file1.jpg\nfile2.jpg\n")), MagicMock())
    result = snap.list_remote_files(fake_ssh, "/remote/folder")
    assert result == {"file1.jpg", "file2.jpg"}


def test_get_local_file_hash(tmp_path):
    f = tmp_path / "test.txt"
    f.write_text("Hello World")
    result = snap.get_local_file_hash(str(f))
    assert isinstance(result, str)
    assert len(result) == 64  # sha256 hash length


def test_get_remote_file_hash_success(fake_ssh):
    fake_ssh.exec_command.return_value = (None, MagicMock(read=MagicMock(return_value=b"abcd1234  /file\n")), MagicMock(read=MagicMock(return_value=b"")))
    result = snap.get_remote_file_hash(fake_ssh, "/file")
    assert result == "abcd1234"


def test_get_remote_file_hash_failure(fake_ssh):
    fake_ssh.exec_command.return_value = (None, MagicMock(read=MagicMock(return_value=b"")), MagicMock(read=MagicMock(return_value=b"error")))
    result = snap.get_remote_file_hash(fake_ssh, "/missing")
    assert result is None

def test_upload_if_different_triggers_upload():
    fake_ssh = MagicMock()

    with patch.object(snap, "get_local_file_hash", return_value="local_hash") as mock_local, \
         patch.object(snap, "get_remote_file_hash", return_value="different_hash") as mock_remote, \
         patch.object(snap, "SCPClient") as mock_scp:

        snap.upload_if_different(fake_ssh, "local.cfg", "remote.cfg")

        mock_local.assert_called_once_with("local.cfg")
        mock_remote.assert_called_once_with(fake_ssh, "remote.cfg")
        mock_scp.return_value.__enter__.return_value.put.assert_called_once_with("local.cfg", "remote.cfg")

def test_upload_if_different_skips_upload(fake_ssh):
    with patch.object(snap, "get_local_file_hash", return_value="same_hash") as mock_local, \
         patch.object(snap, "get_remote_file_hash", return_value="same_hash") as mock_remote, \
         patch.object(snap, "SCPClient") as mock_scp:

        snap.upload_if_different(fake_ssh, "local.cfg", "remote.cfg")
        mock_scp.return_value.__enter__.return_value.put.assert_not_called()


def test_run_remote_script_with_live_output(fake_ssh):
    fake_stdout = MagicMock()
    fake_stdout.channel.exit_status_ready.side_effect = [False, True]
    fake_stdout.channel.recv_ready.return_value = True
    fake_stdout.channel.recv.return_value = b"output\n"
    fake_ssh.exec_command.return_value = (None, fake_stdout, None)

    snap.run_remote_script_with_live_output(fake_ssh, "echo test")
    fake_stdout.channel.recv.assert_called()

def test_snap_runs_full_flow(fake_ssh, tmp_path):
    with patch.object(snap, "list_remote_files", side_effect=[{"a.jpg"}, {"a.jpg", "b.jpg"}]), \
         patch.object(snap, "upload_if_different") as mock_upload, \
         patch.object(snap, "run_remote_script_with_live_output") as mock_run, \
         patch.object(snap, "SCPClient") as mock_scp, \
         patch("GONet_Wizard.commands.snap.GONetConfig") as MockConfig:

        config = MockConfig.return_value
        config.gonet4_path = "/home/pi/gonet4.py"
        config.gonet_config_folder = "/home/pi/config"
        config.gonet_images_folder = "/home/pi/images"
        config.local_output_folder = str(tmp_path)

        # ⚠️ Call the undecorated function to avoid triggering ssh_connect
        snap.take_snapshot.__wrapped__(fake_ssh, "local.cfg")

        mock_upload.assert_called_once()
        mock_run.assert_called_once()
        mock_scp.return_value.__enter__.return_value.get.assert_called_once()

def test_snapshot_download_failure(fake_ssh, tmp_path):
    with patch.object(snap, "list_remote_files", side_effect=[{"a.jpg"}, {"a.jpg", "b.jpg"}]), \
         patch.object(snap, "upload_if_different"), \
         patch.object(snap, "run_remote_script_with_live_output"), \
         patch("GONet_Wizard.commands.snap.GONetConfig") as MockConfig, \
         patch.object(snap, "SCPClient") as mock_scp:

        # Simulate error when .get is called
        mock_scp.return_value.__enter__.return_value.get.side_effect = Exception("Download failed")

        config = MockConfig.return_value
        config.gonet4_path = "/home/pi/gonet4.py"
        config.gonet_config_folder = "/home/pi/config"
        config.gonet_images_folder = "/home/pi/images"
        config.local_output_folder = str(tmp_path)

        with pytest.raises(Exception, match="Download failed"):
            snap.take_snapshot.__wrapped__(fake_ssh, "local.cfg")

def test_snapshot_missing_config_file(fake_ssh):
    with patch.object(snap, "list_remote_files", side_effect=[set(), set()]), \
         patch.object(snap, "run_remote_script_with_live_output"), \
         patch("GONet_Wizard.commands.snap.GONetConfig") as MockConfig, \
         patch.object(snap, "upload_if_different") as mock_upload:

        mock_upload.side_effect = FileNotFoundError("No such file: 'missing.cfg'")

        config = MockConfig.return_value
        config.gonet4_path = "/home/pi/gonet4.py"
        config.gonet_config_folder = "/home/pi/config"
        config.gonet_images_folder = "/home/pi/images"
        config.local_output_folder = "./"

        with pytest.raises(FileNotFoundError, match="missing.cfg"):
            snap.take_snapshot.__wrapped__(fake_ssh, "missing.cfg")

def test_snapshot_script_crash(fake_ssh):
    with patch.object(snap, "list_remote_files", side_effect=[{"old.jpg"}, {"old.jpg"}]), \
         patch.object(snap, "upload_if_different"), \
         patch("GONet_Wizard.commands.snap.GONetConfig") as MockConfig, \
         patch.object(snap, "run_remote_script_with_live_output") as mock_run:

        mock_run.side_effect = RuntimeError("Script crashed")

        config = MockConfig.return_value
        config.gonet4_path = "/home/pi/gonet4.py"
        config.gonet_config_folder = "/home/pi/config"
        config.gonet_images_folder = "/home/pi/images"
        config.local_output_folder = "./"

        with pytest.raises(RuntimeError, match="Script crashed"):
            snap.take_snapshot.__wrapped__(fake_ssh, "config.cfg")

def test_snap_no_config_and_no_new_files(fake_ssh, tmp_path):
    """
    Triggers both:
    - line 189: no config file provided
    - line 214: no new images created
    """
    with patch.object(snap, "list_remote_files", side_effect=[{"only.jpg"}, {"only.jpg"}]), \
         patch.object(snap, "run_remote_script_with_live_output"), \
         patch("GONet_Wizard.commands.snap.GONetConfig") as MockConfig:

        config = MockConfig.return_value
        config.gonet4_path = "/home/pi/gonet4.py"
        config.gonet_config_folder = "/home/pi/config"
        config.gonet_images_folder = "/home/pi/images"
        config.local_output_folder = str(tmp_path)

        # ⚠️ No config file passed
        snap.take_snapshot.__wrapped__(fake_ssh)

        # No exception expected; should print the line at 214


def test_terminate_imaging_success(fake_ssh):
    mock_stdout = MagicMock()
    mock_stdout.read.return_value = "✅ Cleanup complete.".encode("utf-8")

    mock_stderr = MagicMock()
    mock_stderr.read.return_value = b""

    fake_ssh.exec_command.return_value = (None, mock_stdout, mock_stderr)

    # __wrapped__ lets us bypass the @ssh_connect decorator
    terminate.terminate_imaging.__wrapped__(fake_ssh)

    expected_cmd = (
        "crontab -r && "
        "ps aux | grep '[g]onet4.py' | grep -v $$ | awk '{print $2}' | xargs -r kill && "
        "rm -rf /home/pi/Tools/Status/* && "
        "touch /home/pi/Tools/Status/TerminatedAndDisabled! && "
        "echo '✅ Cleanup complete.'"
    )
    fake_ssh.exec_command.assert_called_once_with(expected_cmd)

def test_terminate_imaging_warns_on_error(fake_ssh, capsys):
    mock_stdout = MagicMock()
    mock_stdout.read.return_value = "".encode("utf-8")

    mock_stderr = MagicMock()
    mock_stderr.read.return_value = "crontab: not found".encode("utf-8")

    fake_ssh.exec_command.return_value = (None, mock_stdout, mock_stderr)

    terminate.terminate_imaging.__wrapped__(fake_ssh)

    captured = capsys.readouterr()
    assert "⚠️ Error clearing crontab: crontab: not found" in captured.out

from GONet_Wizard.__main__ import main

def test_cli_dispatch_terminate(monkeypatch):
    with patch("GONet_Wizard.__main__.commands.terminate_imaging") as mock_terminate:
        mock_terminate.return_value = None

        monkeypatch.setattr(sys, "argv", ["GONet_Wizard", "connect", "1.2.3.4", "terminate_imaging"])
        main()
        mock_terminate.assert_called_once_with("1.2.3.4")


def test_cli_dispatch_snap(monkeypatch, tmp_path):
    config_file = tmp_path / "fake_config.cfg"
    config_file.write_text("dummy config")

    with patch("GONet_Wizard.__main__.commands.take_snapshot") as mock_snap:
        mock_snap.return_value = None

        monkeypatch.setattr(sys, "argv", ["GONet_Wizard", "connect", "1.2.3.4", "snap", str(config_file)])
        main()
        mock_snap.assert_called_once_with("1.2.3.4", str(config_file))

def test_require_env_var_uses_default_prompt(monkeypatch):
    monkeypatch.delenv("MISSING_VAR", raising=False)

    with patch("builtins.input", return_value="my_value") as mock_input, \
         patch("builtins.print") as mock_print:
        value = require_env_var("MISSING_VAR")
        assert value == "my_value"
        mock_input.assert_called_once_with("Enter a value for MISSING_VAR: ")
