import os
from dataclasses import dataclass
from dotenv import load_dotenv

load_dotenv()

def require_env_var(name: str, prompt: str = None) -> str:
    """
    Retrieve a required environment variable, or prompt the user to input it.
    """
    value = os.environ.get(name)
    if value is None:
        if prompt is None:
            prompt = f"Enter a value for {name}: "
        print(f"⚠️  Environment variable '{name}' is not set.")
        value = input(prompt)
        print(f"💡 Tip: You can avoid this prompt in the future by setting {name} in your environment or in a .env file.")
    return value

@dataclass
class Config:
    # Defaulted environment variables
    gonet_user: str = os.environ.get("GONET_USER", "pi")
    gonet4_remote_path: str = os.environ.get("GONET4_REMOTE_PATH", "/home/pi/Tools/Camera/gonet4.py")
    gonet_images_folder: str = os.environ.get("GONET_IMAGES_FOLDER", "/home/pi/images/")
    local_output_folder: str = os.environ.get("LOCAL_OUTPUT_FOLDER", "./downloaded_files/")

    # Required environment variables (will prompt if missing).
    # Using a lazy evaluation with property, the user will be
    # prompted only when the variable is needed.
    @property
    def gonet_password(self):
        return require_env_var("GONET_PASSWORD", "Enter GONet SSH password: ")

config = Config()