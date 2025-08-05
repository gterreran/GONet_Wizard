"""
This module provides reusable, self-contained functions for handling JSON
download and loading operations in `Dash <https://dash.plotly.com/>`_ applications. These utilities are
intended to be registered as callbacks and used across different parts of the
GONet Wizard dashboard or other Dash-based tools.

**Functions**

- :func:`.register_json_download`
    Registers a Dash clientside callback for prompting the user to download a
    given Python dictionary as a JSON file.
- :func:`.load_json`
    Decodes a base64-encoded JSON data URL string and returns the parsed Python
    dictionary.

"""


import json, base64

def register_json_download(app, output_component, input_component):
    """
    Register a reusable clientside callback for JSON download.

    **Behavior**:
    - Prompts the user to enter a filename (default: ``.json``).
    - Converts the input dictionary into a formatted JSON string.
    - Creates a Blob and object URL.
    - Initiates the download using a temporary anchor tag.
    - Cleans up all temporary DOM elements and object URLs afterward.

    **Usage Notes**:
    - This approach is quick and convenient for small data payloads.
    - It uses browser-native functionality and does not require server interaction.
    - The callback is designed to be self-contained and avoids the need for backend downloads.
    - A more robust alternative using the File System Access API is commented in the code, but is currently disabled due to limited UI polish and cross-browser compatibility.

    **Future Improvements**:
    - For larger payloads or enhanced control, this behavior may eventually be migrated to the Django backend.

    Parameters
    ----------
    app : dash.Dash
        `Dash <https://dash.plotly.com/>`_ app instance (to register the callback).
    output_component : dash.Output
        The Output where the callback returns (usually a dummy Div).
    input_component : dash.Input
        The Input triggering the download (e.g., a Store's data).
    """
    app.clientside_callback(
        """
        async function(data) {
            if (data) {
                try {
                    const jsonString = JSON.stringify(data, null, 2);
                    const blob = new Blob([jsonString], { type: 'application/json' });

                    const filename = prompt("Please enter the filename:", ".json");
                    if (filename === null || filename.trim() === "") {
                        return window.dash_clientside.no_update;
                    }

                    const url = window.URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    window.URL.revokeObjectURL(url);

                    return "";
                } catch (err) {
                    console.error("Download error:", err);
                    alert("Download failed. Check console for details.");
                    return window.dash_clientside.no_update;
                }
            }
            return window.dash_clientside.no_update;
        }
        """,
        output_component,
        input_component,
        prevent_initial_call=True,
    )

def load_json(contents: str) -> dict:
    """
    Decode a base64-encoded JSON Data URL string and return the parsed dictionary.

    Parameters
    ----------
    contents : :class:`str`
        A data URL string starting with "data:application/json;base64," followed by base64-encoded JSON content.

    Returns
    -------
    :class:`dict`
        The decoded JSON content as a Python dictionary.

    Raises
    ------
    :class:`ValueError`
        If decoding or JSON parsing fails.
    """
    try:
        # Extract base64 part after comma
        encoded = contents.split(',')[1]

        # Fix missing padding if necessary
        padding_needed = (4 - len(encoded) % 4) % 4
        encoded += '=' * padding_needed

        # Decode and parse JSON
        decoded = base64.b64decode(encoded).decode('utf-8')
        return json.loads(decoded)

    except (IndexError, base64.binascii.Error, UnicodeDecodeError, json.JSONDecodeError) as e:
        raise ValueError(f"Invalid JSON base64 data: {e}")

