import threading, webview

class WebviewAPI:
    """
    JavaScript API for PyWebview interactions.

    This object is exposed to JavaScript as `window.pywebview.api`, allowing the
    frontend to call the defined methods.

    """
    
    def close_window(self) -> None:
        """Schedule the destruction of the current PyWebview window."""
        threading.Timer(0.1, lambda: webview.windows[0].destroy()).start()