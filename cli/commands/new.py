import shutil, subprocess, sys
from pathlib import Path
import typer, rich
from agent.utils.fs import ensure_dir
from rich.console import Console

app = typer.Typer(help="Bootstrap a new agent-enabled repo")
console = Console()

DEFAULT_MEMORY_DIRS = ["memory/scratch", "memory/archive", "embeddings"]

@app.command()
def repo(path: Path = typer.Argument(..., help="Target project directory")):
    if path.exists():
        rich.print(f"[red]Error:[/red] {path} already exists.")
        raise typer.Exit(1)
    path.mkdir(parents=True)
    (path / ".cokeydex.yml").write_text("# cokeydex-local config\n")
    for d in DEFAULT_MEMORY_DIRS:
        ensure_dir(path / d)
    console.print(f":white_check_mark: Initialised cokeydex repo at [bold]{path}[/bold]")