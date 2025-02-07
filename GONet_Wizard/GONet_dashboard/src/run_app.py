from .app import app

def run():
    app.run_server(port=8034, mode='inline')

if __name__ == '__main__':
    run()