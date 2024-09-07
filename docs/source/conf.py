import os
import sys
sys.path.insert(0, os.path.abspath('../../'))  # Adjust as necessary
print(sys.path)
print(os.listdir(os.getcwd()))
print(os.listdir(sys.path[0]))

# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'UBC Solar Physics'
copyright = '2024, UBC Solar'
author = 'Joshua Riefman'
release = '0.1.11'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',   # For Google/NumPy style docstrings
    'sphinx.ext.autosummary',  # To generate summary tables for modules
    'myst_parser',           # For Markdown support if needed
]

html_theme = "pydata_sphinx_theme"

autodoc_mock_imports = ['core']
source_suffix = ['.rst', '.md']

templates_path = ['_templates']
exclude_patterns = []
autosummary_generate = True

# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_static_path = ['_static']
