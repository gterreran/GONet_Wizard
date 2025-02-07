from flask import Flask
from jupyter_dash import JupyterDash

server = Flask('GONet_dashboard')
app = JupyterDash(server=server)