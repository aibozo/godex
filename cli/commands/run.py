import typer
from rich.console import Console

app = typer.Typer(help="Execute tasks (placeholder)")
console = Console()

@app.command()
def task():
    """Run a task execution loop"""
    console.print("[yellow]Task execution not yet implemented (Phase VI)[/yellow]")
    raise typer.Exit(1)