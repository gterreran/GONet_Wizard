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

- :class:`EnvVar` : Represents an environment variable with an optional default value.
- :class:`GONetConfig` : Environment settings for interacting with a remote GONet device.
- :class:`DashboardConfig` : Environment settings for dashboard data and image access.

Constants
---------
**GONet variables**

GONET_USER : :class:`EnvVar`
    Environment variable for the GONet user (default name: ``GONET_USER``; default value: ``"pi"``).
GONET_PASSWORD : :class:`EnvVar`
    Environment variable for the GONet password (default name: ``GONET_PASSWORD``).
GONET4_PATH : :class:`EnvVar`
    Environment variable for the path of the ``gonet4.py`` script in a GONet camera (default name: ``GONET4_PATH``; default value: ``"/home/pi/Tools/Camera/gonet4.py"``).
GONET_CONFIG_FOLDER : :class:`EnvVar`
    Environment variable for the path of the folder containing '.config' files in a GONet camera (default name: ``GONET_CONFIG_FOLDER``; default value: ``"/home/pi/Tools/Camera/"``).
GONET_IMAGES_FOLDER : :class:`EnvVar`
    Environment variable for the path of the folder containing the images acquired in a GONet camera (default name: ``GONET_IMAGES_FOLDER``; default value: ``"/home/pi/images/"``).
LOCAL_OUTPUT_FOLDER : :class:`EnvVar`
    Environment variable for the local path of where to download new GONet images (default name: ``LOCAL_OUTPUT_FOLDER``; default value: ``"./downloaded_files/"``).

**Dashboard variables**

GONET_ROOT : :class:`EnvVar`
    Environment variable for the folder containing the json data of extracted GONet data.
GONET_ROOT_IMG : :class:`EnvVar`
    Environment variable for the folder containing the GONet images to visualize.

"""

import os
from pathlib import Path
from dataclasses import dataclass, field
from dotenv import load_dotenv
from typing import Optional

load_dotenv()    

@dataclass
class EnvVar:
    """
    Represents an environment variable with an optional default value.

    This class provides a structured way to define environment variable names
    and their default values, and offers methods to retrieve them from the
    environment safely. Useful for centralizing and managing environment configuration
    in a DRY and maintainable way.

    Attributes
    ----------
    name : str
        The name of the environment variable.
    default : Optional[str], optional
        The default value to use if the environment variable is not set. Defaults to None.

    """
    name: str
    default: Optional[str] = None

    def get(self) -> str:
        """Returns the environment variable's value or its default."""
        return os.environ.get(self.name, self.default)

# Gonet variables 
GONET_USER = EnvVar("GONET_USER", "pi")
GONET_PASSWORD = EnvVar("GONET_PASSWORD")
GONET4_PATH = EnvVar("GONET4_PATH", "/home/pi/Tools/Camera/gonet4.py")
GONET_CONFIG_FOLDER = EnvVar("GONET_CONFIG_FOLDER", "/home/pi/Tools/Camera/")
GONET_IMAGES_FOLDER = EnvVar("GONET_IMAGES_FOLDER", "/home/pi/images/")
LOCAL_OUTPUT_FOLDER = EnvVar("LOCAL_OUTPUT_FOLDER", "./downloaded_files/")

# Dashboard variables
GONET_ROOT = EnvVar("GONET_ROOT")
GONET_ROOT_IMG = EnvVar("GONET_ROOT_IMG")


def require_env_var(envvar: EnvVar, prompt: str = None) -> str:
    """
    Retrieve a required environment variable, or prompt the user to input it.

    This function ensures that a required environment variable is defined.
    If not found, the user is prompted to provide a value.

    Parameters
    ----------
    name : :class:`EnvVar`
        The name of the required environment variable.
    prompt : :class:`str`, optional
        A custom prompt message shown to the user if the variable is not set.

    Returns
    -------
    :class:`str`
        The retrieved or user-provided value for the environment variable.
    """
    value = envvar.get()
    if value is None:
        if prompt is None:
            prompt = f"Enter a value for {envvar.name}: "
        print(f"⚠️  Environment variable '{envvar.name}' is not set.")
        value = input(prompt)
        print(f"💡 Tip: You can avoid this prompt in the future by setting {envvar.name} in your environment or in a .env file.")
    return value


def warn_env_var_missing(envvar: EnvVar, prompt: str = None) -> str | None:
    """
    Warn the user if an optional environment variable is not set.

    This function checks whether a given environment variable is defined.
    If it's missing, the user is prompted to define it interactively.

    To avoid duplicate prompts when running a Dash app in debug mode,
    the function only executes its logic in the reloader child process
    (i.e., when the environment variable ``WERKZEUG_RUN_MAIN`` is set to 'true').

    Parameters
    ----------
    name : :class:`EnvVar`
        The name of the environment variable to check.
    prompt : :class:`str`, optional
        A custom input prompt if the user agrees to define the variable.

    Returns
    -------
    :class:`str` or :class:`None`
        The value of the environment variable if already set or newly defined,
        or None if the user chooses not to define it.

    Notes
    -----
    When `app.run_server(debug=True)` is used in Dash, the server restarts
    itself in a child process for hot reloading. To avoid running this prompt
    logic multiple times, we check for the environment variable
    'WERKZEUG_RUN_MAIN' which is only 'true' in the child process.
    """
    # Only run in main or reloader child process to avoid duplicate prompts
    if os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return None

    value = envvar.get()
    if value is not None:
        return value

    print(f"⚠️  The environment variable '{envvar.name}' is not set. You can still proceed, but some functionalities will not work.")
    choice = input(f"Would you like to define {envvar.name} now? [y/N]: ").strip().lower()

    if choice == 'y':
        if prompt is None:
            prompt = f"Enter a value for {envvar.name}: "
        value = input(prompt).strip()
        os.environ[envvar.name] = value
        print(f"✅ Set {envvar.name} = {value}")
        return value
    else:
        print(f"ℹ️  Skipping {envvar.name}. You can set it later in your environment or .env file.")
        return None


@dataclass
class GONetConfig:
    """
    Environment-based configuration for interacting with a remote GONet device.

    This class retrieves configuration settings from environment variables,
    including SSH credentials, paths to scripts and image directories, and
    local output locations. Environment variables are loaded dynamically at
    runtime to ensure flexibility and testability.

    ⚠️ Implementation Note:
    ------------------------
    Environment variables are not read as default values at class definition time.
    Instead, they are loaded dynamically in the `__post_init__` method.

    Why?
        If fields were defined like: gonet_user: str = GONET_USER.get()
        the environment lookup would occur at **parse time**, not instantiation time.
        This means:

        - Tests using tools like `monkeypatch.setenv()` would not affect behavior.
        - It becomes difficult to override variables dynamically.
        - Test isolation and runtime flexibility are compromised.

    Solution:
        All environment lookups are deferred to `__post_init__()` to ensure they
        reflect the current state of `os.environ` when the object is created.

    Attributes
    ----------
    gonet_user : str
        Username for SSH connection to the GONet device, from `GONET_USER`.
    gonet4_path : str
        Remote path to `gonet4.py`, from `GONET4_PATH`.
    gonet_config_folder : str
        Remote folder containing camera config files, from `GONET_CONFIG_FOLDER`.
    gonet_images_folder : str
        Remote folder where images are stored, from `GONET_IMAGES_FOLDER`.
    local_output_folder : str
        Local folder where downloaded files should be saved, from `LOCAL_OUTPUT_FOLDER`.
    gonet_password : str
        SSH password for the GONet device, from `GONET_PASSWORD`, or prompted interactively.

    """

    gonet_user: str = None
    gonet4_path: str = None
    gonet_config_folder: str = None
    gonet_images_folder: str = None
    local_output_folder: str = None

    def __post_init__(self):
        self.gonet_user = GONET_USER.get()
        self.gonet4_path = GONET4_PATH.get()
        self.gonet_config_folder = GONET_CONFIG_FOLDER.get()
        self.gonet_images_folder = GONET_IMAGES_FOLDER.get()
        self.local_output_folder = LOCAL_OUTPUT_FOLDER.get()
        self.gonet_password = self.get_gonet_password()

    def get_gonet_password(self) -> str:
        """
        SSH password for the GONet device.

        Retrieved from the `GONET_PASSWORD` environment variable,
        or entered interactively if not set.

        Returns
        -------
        :class:`str`
            The SSH password.
        """
        return require_env_var(GONET_PASSWORD, "Enter GONet SSH password: ")


@dataclass
class DashboardConfig:
    """
    Environment-based configuration for the GONet dashboard.

    This class centralizes the retrieval of environment-based paths required
    for the GONet dashboard to function properly. It ensures that environment
    variables are not read until runtime, allowing for dynamic configuration
    and interactive prompting or fallback handling if variables are missing.

    Attributes
    ----------
    dashboard_data_path : :class:`pathlib.Path`
        Absolute path to the root directory where dashboard data is stored.
        Retrieved from the environment variable `GONET_ROOT`. Set during object initialization.
    
    gonet_images_path : :class:`pathlib.Path` or :class:`None`
        Optional absolute path to the directory containing image files for the dashboard.
        Retrieved from the environment variable `GONET_ROOT_IMG`, or set to None if the
        variable is not defined or skipped by the user.

    """

    dashboard_data_path: Path = field(init=False)
    gonet_images_path: Optional[Path] = field(init=False)

    def __post_init__(self):
        self.dashboard_data_path = self.get_dashboard_data_path()
        self.gonet_images_path = self.get_gonet_images_path()


    def get_dashboard_data_path(self) -> Path:
        """
        Path to the dashboard data directory.

        Retrieves the value of the `GONET_ROOT` environment variable and
        converts it to a `Path` object. If the variable is not set, the user
        is prompted to enter a path interactively.

        Returns
        -------
        :class:`pathlib.Path`
            The absolute path defined by the `GONET_ROOT` environment variable.
        """
        gonet_folder_path_str = require_env_var(GONET_ROOT, "Enter the path for the GONet data: ")
        return Path(gonet_folder_path_str)
    
    def get_gonet_images_path(self) -> Path | None:
        """
        Optional path to the image directory for the dashboard.

        Retrieves the value of the `GONET_ROOT_IMG` environment variable and
        converts it to a `Path` object. If the variable is not set or skipped,
        returns None.

        Returns
        -------
        :class:`pathlib.Path` or :class:`None`
            The path defined by the `GONET_ROOT_IMG` environment variable,
            or None if the variable is missing.
        """
        gonet_images_folder_path_str = warn_env_var_missing(GONET_ROOT_IMG, "Enter the path for the GONet images: ")
        if gonet_images_folder_path_str is None:
            return None
        else:
            return Path(gonet_images_folder_path_str)
