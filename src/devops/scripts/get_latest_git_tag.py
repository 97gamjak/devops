"""Script for updating the changelog file."""

import sys

import typer

from devops.git import GitTagError, get_latest_tag
from devops.utils import mstd_print

app = typer.Typer()


@app.command()
def main(*, empty_tag_list_allowed: bool = True) -> None:
    """Retrieve and print the latest git tag.

    Parameters
    ----------
    empty_tag_list_allowed: bool
        Whether to allow an empty tag list without raising an error.

    """
    try:
        latest_tag = get_latest_tag(empty_tag_list_allowed=empty_tag_list_allowed)
        mstd_print(str(latest_tag))
    except GitTagError as e:
        mstd_print(f"❌ Error retrieving latest git tag: {e}")
        sys.exit(1)


if __name__ == "__main__":
    app()
