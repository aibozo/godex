from pathlib import Path
import typer
from rich.console import Console
from agent.config import Settings, get_settings

app = typer.Typer(add_completion=False, rich_markup_mode="rich")
console = Console(highlight=False)

@app.callback(invoke_without_command=True)
def main(
    ctx: typer.Context,
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
    config: Path = typer.Option(
        None, "--config", "-c", exists=True, file_okay=True, dir_okay=False,
        help="Path to .cokeydex.yml (overrides env)"
    ),
):
    """
    :sparkles: [bold cyan]Cokeydex CLI[/bold cyan]
    """
    if verbose:
        console.print(":gear: verbose mode on")
    ctx.obj = get_settings(config_path=config)
    if ctx.invoked_subcommand is None:
        console.print(ctx.get_help())

# Sub-commands imported lazily to cut startup time
from importlib import import_module

for _cmd in ("new", "plan", "run", "usage", "chat", "chat_debug", "chat_llm", "chat_enhanced", "chat_complete", "logs", "broker"):
    mod = import_module(f"cli.commands.{_cmd}")
    # Use a different name for chat_debug, chat_llm, chat_enhanced and chat_complete
    if _cmd == "chat_debug":
        cmd_name = "chat-debug"
    elif _cmd == "chat_llm":
        cmd_name = "chat-llm"
    elif _cmd == "chat_enhanced":
        cmd_name = "chat-enhanced"
    elif _cmd == "chat_complete":
        cmd_name = "chat-complete"
    else:
        cmd_name = _cmd
    app.add_typer(mod.app, name=cmd_name)