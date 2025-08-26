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
    - Detects environment: PyWebview or regular browser.
    - In PyWebview: Calls the exposed `download_json()` API method to handle download.
    - In Browser: Prompts user for filename, creates a Blob, and initiates download.

    **Usage Notes**:
    - Add this only once when initializing the app.
    - `output_component` can be a dummy Div or Store (e.g., Output("download-trigger", "data")).
    - `input_component` should supply a serializable dictionary to download as JSON.

    Parameters
    ----------
    app : dash.Dash
        Dash app instance.
    output_component : dash.Output
        Target output to complete Dash callback structure (can be dummy).
    input_component : dash.Input
        Source of the JSON data to download.
    """
    app.clientside_callback(
        """
        async function(data) {
            if (!data) {
                return window.dash_clientside.no_update;
            }

            try {
                const jsonString = JSON.stringify(data, null, 2);
                const blob = new Blob([jsonString], { type: 'application/json' });

                // Check if PyWebview is available
                if (window.pywebview && window.pywebview.api && typeof window.pywebview.api.download_json === 'function') {
                    await window.pywebview.api.download_json(data);
                } else {
                    const filename = prompt("Please enter the filename:", "data.json");
                    if (!filename || filename.trim() === "") {
                        return window.dash_clientside.no_update;
                    }

                    const url = URL.createObjectURL(blob);
                    const a = document.createElement('a');
                    a.href = url;
                    a.download = filename;
                    document.body.appendChild(a);
                    a.click();
                    document.body.removeChild(a);
                    URL.revokeObjectURL(url);
                }

                return "";
            } catch (err) {
                console.error("Download error:", err);
                alert("Download failed.");
                return window.dash_clientside.no_update;
            }
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

