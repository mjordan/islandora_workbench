from setuptools import setup

setup(
    name="Islandora Workbench",
    version="master",
    author="Mark Jordan",
    author_email="mjordan@sfu",
    description="A command-line tool that allows creation, updating, and deletion of Islandora 8 content.",
    url="https://github.com/mjordan/islandora_workbench",
    license="The Unlicense",
    install_requires=['requests>=2.22,<3', 'ruamel.yaml'],
    python_requires='>=3'
)
