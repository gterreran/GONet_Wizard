from flask import Flask
from dash import Dash
import os

server = Flask('GONet_dashboard')
this_dir = os.path.dirname(__file__)
assets_path = os.path.join(this_dir, 'assets')

app = Dash(server=server, assets_folder=assets_path)