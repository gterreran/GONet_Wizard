from .app import app

def main():
    app.run_server(debug=True)