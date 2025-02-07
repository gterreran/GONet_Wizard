from .app import app

def run():
    app.run_server(mode='inline')

if __name__ == '__main__':
    run()