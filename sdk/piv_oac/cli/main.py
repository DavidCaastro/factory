"""
PIV/OAC CLI entry point.

Usage:
    piv validate <path>   — validate framework specs in a directory
    piv init              — run the 7Q interview and generate specs/active/
"""

import click

from piv_oac.cli.validate import validate
from piv_oac.cli.init_cmd import init
from piv_oac.cli.status import status


@click.group()
@click.version_option(package_name="piv-oac")
def cli() -> None:
    """PIV/OAC framework CLI — validate specs, bootstrap projects, inspect state."""


cli.add_command(validate)
cli.add_command(init)
cli.add_command(status)
