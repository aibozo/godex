import typer
from rich.console import Console

app = typer.Typer(help="Generate task plans (placeholder)")
console = Console()

@app.command()
def generate():
    """Generate a plan for the current task"""
    console.print("[yellow]Plan generation not yet implemented (Phase V)[/yellow]")
    raise typer.Exit(1)