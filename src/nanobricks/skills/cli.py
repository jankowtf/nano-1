"""CLI skill for Nanobricks.

Creates command-line interfaces for nanobricks using Typer.
"""

import asyncio
import json
from typing import Any

from nanobricks.protocol import T_deps, T_in, T_out
from nanobricks.skill import NanobrickEnhanced, Skill, register_skill


@register_skill("cli")
class CliSkill(Skill[T_in, T_out, T_deps]):
    """Creates a command-line interface for a nanobrick.

    Config options:
        - command: Command name (default: brick name)
        - description: Command description
        - input_type: How to parse input (json, text, file)
        - output_format: How to format output (json, text, pretty)
        - auto_create: Create CLI immediately (default: True)
    """

    def _create_enhanced_brick(self, brick):
        # Get config
        command_name = self.config.get("command", brick.name)
        description = self.config.get("description", f"CLI for {brick.name}")
        input_type = self.config.get("input_type", "json")
        output_format = self.config.get("output_format", "json")
        auto_create = self.config.get("auto_create", True)

        class CliEnhanced(NanobrickEnhanced[T_in, T_out, T_deps]):
            def __init__(self, wrapped, skill):
                super().__init__(wrapped, skill)
                self._cli_app = None

                if auto_create:
                    self.create_cli()

            async def invoke(self, input: T_in, *, deps: T_deps | None = None) -> T_out:
                # Normal invocation - just pass through
                return await self._wrapped.invoke(input, deps=deps)

            def create_cli(self) -> Any:
                """Create the Typer CLI app."""
                try:
                    import typer
                    from rich.console import Console
                    from rich.json import JSON as RichJSON
                except ImportError:
                    raise ImportError(
                        "Typer and Rich are required for the CLI skill. "
                        "Install them with: pip install typer rich"
                    )

                # Create Typer app
                app = typer.Typer(
                    name=command_name,
                    help=description,
                    add_completion=True,
                )

                console = Console()

                @app.command()
                def invoke(
                    input_data: str = typer.Argument(
                        ..., help="Input data for the brick"
                    ),
                    from_file: bool = typer.Option(
                        False, "--from-file", "-f", help="Read input from file"
                    ),
                    output_file: str | None = typer.Option(
                        None, "--output", "-o", help="Write output to file"
                    ),
                    pretty: bool = typer.Option(
                        False, "--pretty", "-p", help="Pretty print output"
                    ),
                ):
                    """Invoke the nanobrick from the command line."""
                    try:
                        # Parse input
                        if from_file:
                            with open(input_data) as f:
                                data = f.read()
                        else:
                            data = input_data

                        # Parse based on input type
                        if input_type == "json":
                            try:
                                parsed_input = json.loads(data)
                            except json.JSONDecodeError:
                                console.print("[red]Error: Invalid JSON input[/red]")
                                raise typer.Exit(1)
                        else:
                            parsed_input = data

                        # Run the brick (handle async)
                        result = asyncio.run(self._wrapped.invoke(parsed_input))

                        # Format output
                        if output_format == "json" or pretty:
                            if pretty:
                                output = RichJSON.from_data(result)
                                console.print(output)
                            else:
                                output = json.dumps(result)
                                if output_file:
                                    with open(output_file, "w") as f:
                                        f.write(output)
                                else:
                                    print(output)
                        else:
                            output = str(result)
                            if output_file:
                                with open(output_file, "w") as f:
                                    f.write(output)
                            else:
                                print(output)

                    except Exception as e:
                        console.print(f"[red]Error: {type(e).__name__}: {str(e)}[/red]")
                        raise typer.Exit(1)

                @app.command()
                def info():
                    """Show information about this nanobrick."""
                    console.print(f"[bold]Nanobrick:[/bold] {self._wrapped.name}")
                    console.print(f"[bold]Version:[/bold] {self._wrapped.version}")
                    console.print(f"[bold]Type:[/bold] {type(self._wrapped).__name__}")

                    # Show docstring if available
                    if self._wrapped.__class__.__doc__:
                        console.print("\n[bold]Description:[/bold]")
                        console.print(self._wrapped.__class__.__doc__.strip())

                @app.command()
                def example():
                    """Show example usage."""
                    example_input = {"key": "value", "number": 42}
                    console.print("[bold]Example Input:[/bold]")
                    console.print(RichJSON.from_data(example_input))

                    console.print("\n[bold]Command:[/bold]")
                    console.print(
                        f"{command_name} invoke '{json.dumps(example_input)}'"
                    )

                    console.print("\n[bold]From file:[/bold]")
                    console.print(f"echo '{json.dumps(example_input)}' > input.json")
                    console.print(f"{command_name} invoke input.json --from-file")

                self._cli_app = app
                return app

            def run_cli(self):
                """Run the CLI application."""
                if not self._cli_app:
                    self.create_cli()

                self._cli_app()

        return CliEnhanced(brick, self)
