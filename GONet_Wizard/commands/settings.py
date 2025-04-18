"""
Environment Configuration and Variable Management.

This module provides utility functions and configuration classes for handling
environment variables used by the GONet Wizard system, in particular for its 
entry points and various command-line tools. It includes validation
tools that either require or gently warn about missing variables, as well as
data classes that organize related environment values for dashboard and
camera-side operations.

**Functions**

- :func:`require_env_var` : Prompt for required environment variables if missing.
- :func:`warn_env_var_missing` : Prompt optionally for missing environment variables.

**Classes**

- :class:`GONetConfig` : Environment settings for interacting with a remote GONet device.
- :class:`DashboardConfig` : Environment settings for dashboard data and image access.

"""

import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()


def require_env_var(name: str, prompt: str = None) -> str:
    """
    Retrieve a required environment variable, or prompt the user to input it.

    This function ensures that a required environment variable is defined.
    If not found, the user is prompted to provide a value.

    Parameters
    ----------
    name : :class:`str`
        The name of the required environment variable.
    prompt : :class:`str`, optional
        A custom prompt message shown to the user if the variable is not set.

    Returns
    -------
    :class:`str`
        The retrieved or user-provided value for the environment variable.
    """
    value = os.environ.get(name)
    if value is None:
        if prompt is None:
            prompt = f"Enter a value for {name}: "
        print(f"⚠️  Environment variable '{name}' is not set.")
        value = input(prompt)
        print(f"💡 Tip: You can avoid this prompt in the future by setting {name} in your environment or in a .env file.")
    return value


def warn_env_var_missing(name: str, prompt: str = None) -> str | None:
    """
    Warn the user if an optional environment variable is not set.

    If the variable is missing, the user is asked whether they want to define it now.
    If confirmed, the value is stored in :py:data:`os.environ` for the current session only.

    Parameters
    ----------
    name : :class:`str`
        The name of the environment variable to check.
    prompt : :class:`str`, optional
        A custom input prompt if the user agrees to define the variable.

    Returns
    -------
    :class:`str` or :class:`None`
        The value of the environment variable, or None if skipped.
    """
    value = os.environ.get(name)

    if value is not None:
        return value

    print(f"⚠️  The environment variable '{name}' is not set. You can still proceed, but some functionalities will not work.")
    choice = input(f"Would you like to define {name} now? [y/N]: ").strip().lower()

    if choice == 'y':
        if prompt is None:
            prompt = f"Enter a value for {name}: "
        value = input(prompt).strip()
        os.environ[name] = value
        print(f"✅ Set {name} = {value}")
        return value
    else:
        print(f"ℹ️  Skipping {name}. You can set it later in your environment or .env file.")
        return None


@dataclass
class GONetConfig:
    """
    Environment-based configuration for interacting with a remote GONet device.

    Attributes
    ----------
    gonet_user : :class:`str`
        Username for SSH connection to the GONet device. Defaults to `pi`.
    gonet4_path : :class:`str`
        Remote path to the gonet4.py script on the GONet device. Defaults to `/home/pi/Tools/Camera/gonet4.py`.
    gonet_config_folder : :class:`str`
        Directory on the GONet device where configuration files are stored. Defaults to `/home/pi/Tools/Camera/`.
    gonet_images_folder : :class:`str`
        Directory on the GONet device where captured images are saved. Defaults to `/home/pi/images/`.
    local_output_folder : :class:`str`
        Local path where downloaded files should be stored. Defaults to `./downloaded_files/`.
    """

    gonet_user: str = os.environ.get("GONET_USER", "pi")
    gonet4_path: str = os.environ.get("GONET4_PATH", "/home/pi/Tools/Camera/gonet4.py")
    gonet_config_folder: str = os.environ.get("GONET_CONFIG_FOLDER", "/home/pi/Tools/Camera/")
    gonet_images_folder: str = os.environ.get("GONET_IMAGES_FOLDER", "/home/pi/images/")
    local_output_folder: str = os.environ.get("LOCAL_OUTPUT_FOLDER", "./downloaded_files/")

    @property
    def gonet_password(self) -> str:
        """
        SSH password for the GONet device.

        Retrieved interactively if not set via the ``GONET_PASSWORD`` environment variable.

        Returns
        -------
        :class:`str`
            The SSH password.
        """
        return require_env_var("GONET_PASSWORD", "Enter GONet SSH password: ")


@dataclass
class DashboardConfig:
    """
    Environment-based configuration used by the GONet dashboard.

    This class defers retrieval of environment variables until accessed.

    """

    @property
    def dashboard_data_path(self) -> str:
        """
        Path to the dashboard data directory.

        Returns
        -------
        :class:`str`
            The absolute path defined by the ``GONET_ROOT`` environment variable.
        """
        return require_env_var("GONET_ROOT", "Enter the path for the GONet data: ")
    
    @property
    def gonet_images_path(self) -> str | None:
        """
        Optional path to image directory for the dashboard.

        Returns
        -------
        :class:`str` or :class:`None`
            The path defined by ``ROOT_EXT``, or None if skipped.
        """
        return warn_env_var_missing("ROOT_EXT", "Enter the path for the GONet images: ")
