import os
import sys
import subprocess

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

project = 'UBC Solar Simulation'
copyright = '2024, UBC Solar'
author = 'Joshua Riefman'
release = '0.1.11'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.napoleon',
    'sphinx.ext.autosummary',
    'sphinx.ext.linkcode',
    'myst_parser',
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


def get_commit_hash():
    try:
        return subprocess.check_output(['git', 'rev-parse', 'HEAD']).strip().decode('utf-8')
    except subprocess.CalledProcessError:
        return "main"


def linkcode_resolve(domain, info):
    if domain != 'py':
        return None
    if not info['module']:
        return None

    filename = info['module'].replace('.', '/')
    return f"https://github.com/UBC-Solar/Simulation/blob/{get_commit_hash()}/{filename}.py"
