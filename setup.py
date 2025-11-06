from setuptools import setup

setup(
    name="Islandora Workbench",
    version="0.1.dev0",
    author="Mark Jordan",
    author_email="mjordan@sfu",
    description="A command-line tool that allows creation, updating, and deletion of Islandora content.",
    url="https://github.com/mjordan/islandora_workbench",
    license="MIT",
    install_requires=[
        "requests>=2.22,<3",
        "requests_cache>=1.1",
        "ruamel.yaml<=0.17.21",
        "ruamel.yaml.clib<=0.2.12",
        "pyparsing<3.2",
        "progress_bar",
        "openpyxl",
        "unidecode",
        "edtf_validate",
        "typing-extensions>=4.14.0",
        "rich",
    ],
    python_requires=">=3.9",
    py_modules=[],
)
