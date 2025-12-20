"""Script to generate a default TOML configuration template file."""

import typer

from devops import __GLOBAL_CONFIG__

app = typer.Typer(help="TOML template generator.")


@app.command()
def generate_toml_template() -> None:
    """Generate a default TOML configuration template file."""
    __GLOBAL_CONFIG__.write_default()
