from GONet_Wizard.GONet_utils.src.gonetfile import GONetFile
from typing import Union, List
import pprint, os

def show_meta(files: Union[str, List[str]]) -> None:
    '''
    Show metadata of one or more GONet files.

    Parameters:
        files (str or list of str): Path(s) to GONet files.
    '''

    if isinstance(files, str):
        files = [files]

    for path in files:
        print(f"\n📂 File: {path}")
        if not os.path.isfile(path):
            print("   ❌ File does not exist.")
            continue

        try:
            go = GONetFile.from_file(path)
            print("🧾 Metadata:")
            pprint.pprint(go.meta, indent=4, width=100)
        except Exception as e:
            print(f"   ⚠️ Error reading metadata: {e}")