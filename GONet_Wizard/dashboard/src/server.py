from flask import Flask
from dash import Dash

server = Flask('GONet_dashboard')
app = Dash(server=server)