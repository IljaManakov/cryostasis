from pathlib import Path

# -- Project information -----------------------------------------------------

project = 'cryostasis'
copyright = '2025, Ilja Manakov'
author = 'Ilja Manakov'
with open(Path(__file__).parent.parent.parent / "src" / "cryostasis" / "version.txt") as version_file:
    version = version_file.read().strip()
    release = version
copyright = "2025, Ilja Manakov"

# -- General configuration ---------------------------------------------------

extensions = [
    'sphinx.ext.napoleon',
    'sphinx_rtd_theme',
    'sphinx.ext.autodoc',
    'myst_parser',
]

templates_path = ['_templates']
exclude_patterns = []

language = 'en'

# -- Options for HTML output -------------------------------------------------

html_theme = 'sphinx_rtd_theme'
html_context = {
    "display_github": True,
    "github_user": "IljaManakov",
    "github_repo": "cryostasis",
    "github_version": "main",
    "conf_py_path": "/doc/src/",
}

# -- Options for autodoc -----------------------------------------------------

autoclass_content = 'both'
autodoc_member_order = 'groupwise'
# autodoc_typehints = 'both'
