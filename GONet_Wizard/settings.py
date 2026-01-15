# GONet_Wizard/settings.py

"""
Environment Configuration and Variable Management
=================================================

This module centralizes environment-driven configuration used across GONet
Wizard. It defines small helpers and data containers for reading values from
``os.environ`` (optionally via a ``.env`` file) and for collecting related
settings into structured objects.

The primary abstraction is :class:`.EnvVar`, which represents a named
environment variable with an optional default value. :func:`require_env_var`
builds on that to ensure required values are available, prompting the user when
needed.

Constants
---------
ROOT : :class:`pathlib.Path`
    Absolute path to the GONet_Wizard package root directory.
STATIC : :class:`pathlib.Path`
    Absolute path to the shared static assets folder.

GONET_USER : :class:`.EnvVar`
    Environment variable for the remote GONet username (default: ``"pi"``).
GONET_PASSWORD : :class:`.EnvVar`
    Environment variable for the remote GONet password (no default).
GONET4_PATH : :class:`.EnvVar`
    Environment variable for the remote ``gonet4.py`` path
    (default: ``"/home/pi/Tools/Camera/gonet4.py"``).
GONET_CONFIG_FOLDER : :class:`.EnvVar`
    Environment variable for the remote configuration folder path
    (default: ``"/home/pi/Tools/Camera/"``).
GONET_IMAGES_FOLDER : :class:`.EnvVar`
    Environment variable for the remote image folder path
    (default: ``"/home/pi/images/"``).
LOCAL_OUTPUT_FOLDER : :class:`.EnvVar`
    Environment variable for the local download destination
    (default: ``"./downloaded_files/"``).

DASHBOARD_DEBUG : :class:`.EnvVar`
    Environment variable controlling dashboard debug behavior
    (default: ``False``).

Functions
---------
:func:`require_env_var`
    Retrieve a required environment variable, prompting the user if missing.

Classes
-------
:class:`EnvVar`
    Representation of a named environment variable with an optional default.
:class:`GONetConfig`
    Environment-based configuration for interacting with a remote GONet device.

"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv


load_dotenv()


@dataclass
class EnvVar:
    """
    Representation of an environment variable with an optional default value.

    Instances of this class centralize variable names and defaults, and provide
    a consistent accessor via :meth:`get`.

    Attributes
    ----------
    name : :class:`str`
        Name of the environment variable.
    default : :class:`object`, optional
        Default value used when the environment variable is not present.
        Defaults to ``None``.
    """

    name: str
    default: Optional[Any] = None

    def get(self) -> Optional[Any]:
        """
        Retrieve the environment variable value or its default.

        If the variable exists in the environment and is a string, leading and
        trailing whitespace are stripped. If the resulting string is empty, the
        value is treated as missing and ``None`` is returned.

        Returns
        -------
        :class:`object`, optional
            The value of the environment variable, the configured default, or
            ``None`` if the variable is unset (or set to an empty string).
        """
        val: Any = os.environ.get(self.name, self.default)
        if isinstance(val, str):
            val = val.strip()
            if val == "":
                return None
        return val


# Absolute path to the GONet_Wizard/ root directory
ROOT = Path(__file__).resolve().parent

# Absolute path to the shared static folder
STATIC = ROOT / "static"

# GONet variables
GONET_USER = EnvVar("GONET_USER", "pi")
GONET_PASSWORD = EnvVar("GONET_PASSWORD")
GONET4_PATH = EnvVar("GONET4_PATH", "/home/pi/Tools/Camera/gonet4.py")
GONET_CONFIG_FOLDER = EnvVar("GONET_CONFIG_FOLDER", "/home/pi/Tools/Camera/")
GONET_IMAGES_FOLDER = EnvVar("GONET_IMAGES_FOLDER", "/home/pi/images/")
LOCAL_OUTPUT_FOLDER = EnvVar("LOCAL_OUTPUT_FOLDER", "./downloaded_files/")

# Dashboard variables
DASHBOARD_DEBUG = EnvVar("DASHBOARD_DEBUG", False)


def require_env_var(envvar: EnvVar, prompt: Optional[str] = None) -> str:
    """
    Retrieve a required environment variable, or prompt the user to input it.

    This function ensures a required value is available. If the variable is not
    set (or is set to an empty string), the user is prompted for a value.

    Parameters
    ----------
    envvar : :class:`.EnvVar`
        Environment variable descriptor for the required value.
    prompt : :class:`str`, optional
        Custom prompt shown to the user if the variable is missing.

    Returns
    -------
    :class:`str`
        The retrieved or user-provided value.

    Raises
    ------
    EOFError
        If user input is required but cannot be read (e.g., stdin closed).
    """
    value = envvar.get()
    if value is None:
        if prompt is None:
            prompt = f"Enter a value for {envvar.name}: "
        print(f"⚠️  Environment variable '{envvar.name}' is not set.")
        value = input(prompt)
        print(
            f"💡 Tip: You can avoid this prompt in the future by setting "
            f"{envvar.name} in your environment or in a .env file."
        )
    return str(value)


@dataclass
class GONetConfig:
    """
    Environment-based configuration for interacting with a remote GONet device.

    Values are loaded from environment variables at instantiation time (in
    :meth:`__post_init__`) to support test overrides (e.g.,
    ``monkeypatch.setenv``) and runtime reconfiguration.

    Attributes
    ----------
    gonet_user : :class:`str`, optional
        Username for SSH connection to the GONet device (from ``GONET_USER``).
    gonet4_path : :class:`str`, optional
        Remote path to ``gonet4.py`` (from ``GONET4_PATH``).
    gonet_config_folder : :class:`str`, optional
        Remote folder containing camera config files (from ``GONET_CONFIG_FOLDER``).
    gonet_images_folder : :class:`str`, optional
        Remote folder where images are stored (from ``GONET_IMAGES_FOLDER``).
    local_output_folder : :class:`str`, optional
        Local folder where downloaded files should be saved (from ``LOCAL_OUTPUT_FOLDER``).
    gonet_password : :class:`str`, optional
        SSH password for the GONet device. Loaded from ``GONET_PASSWORD`` or
        prompted for interactively if missing.
    """

    gonet_user: Optional[str] = None
    gonet4_path: Optional[str] = None
    gonet_config_folder: Optional[str] = None
    gonet_images_folder: Optional[str] = None
    local_output_folder: Optional[str] = None
    gonet_password: Optional[str] = None

    def __post_init__(self) -> None:
        """
        Populate configuration values from the current environment.

        Returns
        -------
        None
        """
        self.gonet_user = str(GONET_USER.get()) if GONET_USER.get() is not None else None
        self.gonet4_path = str(GONET4_PATH.get()) if GONET4_PATH.get() is not None else None
        self.gonet_config_folder = (
            str(GONET_CONFIG_FOLDER.get()) if GONET_CONFIG_FOLDER.get() is not None else None
        )
        self.gonet_images_folder = (
            str(GONET_IMAGES_FOLDER.get()) if GONET_IMAGES_FOLDER.get() is not None else None
        )
        self.local_output_folder = (
            str(LOCAL_OUTPUT_FOLDER.get()) if LOCAL_OUTPUT_FOLDER.get() is not None else None
        )
        self.gonet_password = self.get_gonet_password()

    def get_gonet_password(self) -> str:
        """
        Retrieve the SSH password for the GONet device.

        The password is read from ``GONET_PASSWORD`` when available; otherwise
        the user is prompted interactively.

        Returns
        -------
        :class:`str`
            The SSH password.

        Raises
        ------
        EOFError
            If user input is required but cannot be read (e.g., stdin closed).
        """
        return require_env_var(GONET_PASSWORD, "Enter GONet SSH password: ")
