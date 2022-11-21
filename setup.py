from setuptools import setup

setup(
    name="Islandora Workbench",
    version="0.1.dev0",
    author="Mark Jordan",
    author_email="mjordan@sfu",
    description="A command-line tool that allows creation, updating, and deletion of Islandora content.",
    url="https://github.com/mjordan/islandora_workbench",
    license="MIT",
    install_requires=['requests>=2.22,<3', 'requests_cache', 'iteration_utilities', 'ruamel.yaml', 'progress_bar', 'openpyxl', 'unidecode', 'edtf_validate', 'rich'],
    python_requires='>=3.7',
    py_modules=[]
)
