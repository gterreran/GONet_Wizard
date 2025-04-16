import os
import sys
sys.path.insert(0, os.path.abspath('../../'))
from typing import Callable, Any

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'GONet Wizard'
copyright = '2025, Giacomo Terreran'
author = 'Giacomo Terreran'

# The master toctree document (this is the main entry point for Sphinx)
master_doc = 'index'

# The suffix of source files. Typically .rst for reStructuredText files
source_suffix = {'.rst': 'restructuredtext'}

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',  # For Google-style docstrings
    'sphinx.ext.viewcode',  # To include links to source code
    'sphinx.ext.intersphinx', # Enables linking to external docs
    'sphinx_autodoc_typehints',  
    'sphinx.ext.extlinks',
]

exclude_patterns = []

typehints = 'signature'
autodoc_typehints = 'description'

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'sphinx_rtd_theme'
html_static_path = ['_static']
html_logo = '_static/logo.png'  # Path to your logo image

intersphinx_mapping = {
    'python': ('https://docs.python.org/3', None),
    'PIL': ('https://pillow.readthedocs.io/en/stable/', None),
    'paramiko': ('https://docs.paramiko.org/en/stable', None),
    'numpy': ('https://numpy.org/doc/stable', None),
    'astropy': ('https://docs.astropy.org/en/stable/', None),
    'flask': ('https://flask.palletsprojects.com/en/latest/', None),
}

extlinks = {
    'dashdoc': ('https://dash.plotly.com/%s', 'dash.'),
}

autodoc_typehints = 'signature'
autodoc_member_order = 'bysource'

html_theme_options = {
    "navigation_depth": 3,  # Required for function-level sidebar nesting
}