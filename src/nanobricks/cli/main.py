"""Main CLI for nanobricks."""

from pathlib import Path

import typer
from rich.console import Console
from rich.progress import track

from .scaffold import app as scaffold_app

console = Console()

app = typer.Typer(
    name="nanobrick",
    help="Nanobricks CLI - Build antifragile components",
    no_args_is_help=True,
)

# Add subcommands
app.add_typer(scaffold_app, name="new", help="Create new nanobrick projects")

# Create docs subcommand group
docs_app = typer.Typer(help="Documentation generation commands")
app.add_typer(docs_app, name="docs")


@docs_app.command("generate")
def generate_docs(
    paths: list[Path] = typer.Argument(
        None, help="Paths to search for nanobricks (defaults to current directory)"
    ),
    output: Path = typer.Option(
        Path("docs/generated"),
        "--output",
        "-o",
        help="Output directory for documentation",
    ),
    formats: list[str] = typer.Option(
        ["markdown", "json"],
        "--format",
        "-f",
        help="Output formats (markdown, json, html)",
    ),
    include_examples: bool = typer.Option(
        True, "--examples/--no-examples", help="Include usage examples"
    ),
    include_diagrams: bool = typer.Option(
        True, "--diagrams/--no-diagrams", help="Include composition diagrams"
    ),
):
    """Generate documentation for nanobricks."""
    from nanobricks.docs.enhanced_generator import EnhancedDocumentationGenerator

    # Default to current directory if no paths provided
    if not paths:
        paths = [Path.cwd()]

    # Validate formats
    valid_formats = {"markdown", "json", "html"}
    invalid_formats = set(formats) - valid_formats
    if invalid_formats:
        console.print(f"[red]Error: Invalid formats: {invalid_formats}[/red]")
        console.print(f"Valid formats: {valid_formats}")
        raise typer.Exit(1)

    try:
        generator = EnhancedDocumentationGenerator(
            output_dir=output,
            include_examples=include_examples,
            include_diagrams=include_diagrams,
        )

        console.print("[green]Generating documentation...[/green]")
        console.print(f"Search paths: {[str(p) for p in paths]}")
        console.print(f"Output directory: {output}")
        console.print(f"Formats: {formats}")

        # Discover bricks
        bricks = []
        for path in track(paths, description="Discovering nanobricks..."):
            bricks.extend(generator.discover_bricks([path]))

        console.print(f"[blue]Found {len(bricks)} nanobricks[/blue]")

        # Generate documentation
        if "markdown" in formats:
            with console.status("Generating markdown documentation..."):
                generator.generate_markdown(bricks)
            console.print("[green]✓ Markdown documentation generated[/green]")

        if "json" in formats:
            with console.status("Generating JSON documentation..."):
                generator.generate_json(bricks)
            console.print("[green]✓ JSON documentation generated[/green]")

        if "html" in formats:
            console.print("[yellow]HTML generation not yet implemented[/yellow]")

        console.print(f"\n[green]Documentation generated in: {output}[/green]")

    except Exception as e:
        console.print(f"[red]Error generating documentation: {e}[/red]")
        raise typer.Exit(1)


@docs_app.command("serve")
def serve_docs(
    port: int = typer.Option(8000, "--port", "-p", help="Port to serve on"),
    docs_dir: Path = typer.Option(
        Path("docs/generated"), "--dir", "-d", help="Documentation directory to serve"
    ),
):
    """Serve generated documentation locally."""
    import http.server
    import os
    import socketserver

    if not docs_dir.exists():
        console.print(
            f"[red]Error: Documentation directory not found: {docs_dir}[/red]"
        )
        console.print("Run 'nanobrick docs generate' first to create documentation.")
        raise typer.Exit(1)

    os.chdir(docs_dir)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format, *args):
            # Custom logging
            console.print(f"[dim]{self.address_string()} - {format % args}[/dim]")

    with socketserver.TCPServer(("", port), Handler) as httpd:
        console.print(
            f"[green]Serving documentation at http://localhost:{port}[/green]"
        )
        console.print("[dim]Press Ctrl+C to stop[/dim]")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            console.print("\n[yellow]Stopping server...[/yellow]")


@app.command()
def version():
    """Show nanobricks version."""
    from nanobricks import __version__

    console.print(f"nanobricks version: {__version__}")


def main():
    """Main entry point for the CLI."""
    app()


if __name__ == "__main__":
    main()
