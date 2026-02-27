"""Developer tools for monokl."""

import json
import typing as t
import uuid as uuid_lib

import typer

tools_app = typer.Typer(
    name="tool",
    help="Collection of useful developer tools",
    no_args_is_help=True,
)


@tools_app.command()
def uuid(
    count: t.Annotated[int, typer.Option("--count", "-n", help="Number of UUIDs to generate")] = 1,
    output_format: t.Annotated[
        str, typer.Option("--format", "-f", help="Output format: text or json")
    ] = "text",
    uppercase: t.Annotated[
        bool, typer.Option("--uppercase", "-u", help="Uppercase output")
    ] = False,
    no_hyphens: t.Annotated[
        bool, typer.Option("--no-hyphens", help="Remove hyphens from output")
    ] = False,
) -> None:
    """Generate UUID4 strings."""
    if count < 1:
        typer.echo("Error: count must be at least 1", err=True)
        raise typer.Exit(1)

    uuids = []
    for _ in range(count):
        u = str(uuid_lib.uuid4())
        if no_hyphens:
            u = u.replace("-", "")
        if uppercase:
            u = u.upper()
        uuids.append(u)

    if output_format == "json":
        typer.echo(json.dumps(uuids))
    else:
        for u in uuids:
            typer.echo(u)
