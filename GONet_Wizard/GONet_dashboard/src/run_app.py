from .app import app

def run():
    app.run_server(debug=True)

if __name__ == '__main__':
    run()