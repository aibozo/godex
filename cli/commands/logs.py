# CLI commands for viewing and managing LLM logs
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.text import Text
import json
from pathlib import Path
from datetime import datetime

from agent.utils.llm_logger import get_llm_logger

app = typer.Typer()
console = Console()

@app.command()
def stats():
    """Show logging statistics"""
    logger = get_llm_logger()
    stats = logger.get_stats()
    
    # Create main stats table
    table = Table(title="LLM Logging Statistics", show_header=True)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Total Logs", str(stats["total_logs"]))
    table.add_row("Total Errors", str(stats["errors"]))
    table.add_row("Success Rate", f"{((stats['total_logs'] - stats['errors']) / max(stats['total_logs'], 1) * 100):.1f}%")
    
    console.print(table)
    
    # Create component breakdown table
    if stats["by_component"]:
        comp_table = Table(title="By Component", show_header=True)
        comp_table.add_column("Component", style="cyan")
        comp_table.add_column("Total", style="white")
        comp_table.add_column("Success", style="green")
        comp_table.add_column("Errors", style="red")
        
        for component, data in stats["by_component"].items():
            comp_table.add_row(
                component,
                str(data["total"]),
                str(data["success"]),
                str(data["errors"])
            )
        
        console.print("\n")
        console.print(comp_table)

@app.command()
def recent(
    component: str = typer.Option(None, "--component", "-c", help="Filter by component"),
    limit: int = typer.Option(10, "--limit", "-n", help="Number of logs to show"),
    errors_only: bool = typer.Option(False, "--errors", "-e", help="Show only errors")
):
    """Show recent log entries"""
    logger = get_llm_logger()
    
    if errors_only:
        logs = logger.get_error_logs(component=component, limit=limit)
        title = "Recent Error Logs"
    elif component:
        logs = logger.get_recent_logs(component=component, limit=limit)
        title = f"Recent Logs: {component}"
    else:
        # Get logs from all components
        all_logs = []
        for comp_dir in logger.log_dir.iterdir():
            if comp_dir.is_dir():
                all_logs.extend(logger.get_recent_logs(comp_dir.name, limit=limit))
        # Sort by timestamp and limit
        logs = sorted(all_logs, key=lambda x: x.get("timestamp", ""), reverse=True)[:limit]
        title = "Recent Logs (All Components)"
    
    if not logs:
        console.print("[yellow]No logs found[/yellow]")
        return
    
    # Display logs
    for i, log in enumerate(logs):
        # Create summary panel
        timestamp = log.get("timestamp", "Unknown")
        component = log.get("component", "unknown")
        model = log.get("model", "unknown")
        status = log.get("status", "unknown")
        filename = log.get("_filename", "unknown")
        
        # Format timestamp nicely
        try:
            dt = datetime.fromisoformat(timestamp)
            timestamp_str = dt.strftime("%Y-%m-%d %H:%M:%S")
        except:
            timestamp_str = timestamp
        
        # Status color
        status_color = "green" if status == "success" else "red"
        
        # Create header
        header = f"[{status_color}]{status.upper()}[/{status_color}] | {component} | {model} | {timestamp_str}"
        
        # Get message preview
        messages = log.get("input", {}).get("messages", [])
        if messages:
            last_msg = messages[-1]
            role = last_msg.get("role", "unknown")
            content = last_msg.get("content", "")[:100] + "..." if len(last_msg.get("content", "")) > 100 else last_msg.get("content", "")
            preview = f"[dim]{role}:[/dim] {content}"
        else:
            preview = "[dim]No messages[/dim]"
        
        # Show error if present
        error = log.get("output", {}).get("error")
        if error:
            preview = f"[red]Error:[/red] {error[:100]}..."
        
        panel = Panel(
            preview,
            title=header,
            subtitle=f"[dim]{filename}[/dim]",
            border_style="blue" if status == "success" else "red"
        )
        console.print(panel)

@app.command()
def view(filename: str):
    """View a specific log file"""
    logger = get_llm_logger()
    
    # Try to find the file
    file_path = None
    for comp_dir in logger.log_dir.iterdir():
        if comp_dir.is_dir():
            potential_path = comp_dir / filename
            if potential_path.exists():
                file_path = potential_path
                break
    
    if not file_path:
        console.print(f"[red]Log file not found: {filename}[/red]")
        console.print("\n[yellow]Tip: Use 'logs recent' to see available log files[/yellow]")
        return
    
    # Load and display the log
    try:
        with open(file_path, 'r') as f:
            log_data = json.load(f)
        
        # Display header info
        console.print(Panel(
            f"Component: {log_data.get('component', 'unknown')}\n"
            f"Model: {log_data.get('model', 'unknown')}\n"
            f"Status: {log_data.get('status', 'unknown')}\n"
            f"Timestamp: {log_data.get('timestamp', 'unknown')}",
            title="Log Details",
            border_style="cyan"
        ))
        
        # Display input messages
        console.print("\n[bold cyan]Input Messages:[/bold cyan]")
        messages = log_data.get("input", {}).get("messages", [])
        for i, msg in enumerate(messages):
            role = msg.get("role", "unknown")
            content = msg.get("content", "")
            
            # Color code by role
            role_color = {
                "system": "yellow",
                "user": "green",
                "assistant": "blue",
                "tool": "magenta"
            }.get(role, "white")
            
            console.print(f"\n[{role_color}]═══ {role.upper()} ═══[/{role_color}]")
            console.print(Text(content, style="white"))
        
        # Display response
        console.print("\n[bold cyan]Response:[/bold cyan]")
        response = log_data.get("output", {}).get("response")
        error = log_data.get("output", {}).get("error")
        
        if error:
            console.print(f"[red]Error: {error}[/red]")
        elif isinstance(response, str):
            console.print(Text(response, style="white"))
        elif isinstance(response, dict):
            console.print(Syntax(json.dumps(response, indent=2), "json"))
        else:
            console.print(str(response))
        
        # Display metadata
        if log_data.get("metadata"):
            console.print("\n[bold cyan]Metadata:[/bold cyan]")
            console.print(Syntax(json.dumps(log_data["metadata"], indent=2), "json"))
        
        # Display stats
        stats = log_data.get("stats", {})
        if stats:
            console.print(f"\n[dim]Input chars: {stats.get('input_chars', 0)} | Output chars: {stats.get('output_chars', 0)}[/dim]")
        
    except Exception as e:
        console.print(f"[red]Error reading log file: {e}[/red]")

@app.command()
def clear(
    component: str = typer.Option(None, "--component", "-c", help="Clear logs for specific component"),
    older_than: int = typer.Option(None, "--older-than", "-o", help="Only clear logs older than N hours"),
    confirm: bool = typer.Option(False, "--yes", "-y", help="Skip confirmation")
):
    """Clear log files"""
    logger = get_llm_logger()
    
    # Show what will be deleted
    if component:
        target = f"logs for component '{component}'"
    else:
        target = "all logs"
    
    if older_than:
        target += f" older than {older_than} hours"
    
    if not confirm:
        confirm = typer.confirm(f"Delete {target}?")
    
    if not confirm:
        console.print("[yellow]Cancelled[/yellow]")
        return
    
    # Clear logs
    deleted = logger.clear_logs(component=component, older_than_hours=older_than)
    console.print(f"[green]Deleted {deleted} log files[/green]")

@app.command()
def search(
    query: str,
    component: str = typer.Option(None, "--component", "-c", help="Search in specific component"),
    limit: int = typer.Option(20, "--limit", "-n", help="Maximum results")
):
    """Search log contents"""
    logger = get_llm_logger()
    query_lower = query.lower()
    
    # Search through logs
    matches = []
    
    if component:
        comp_dirs = [logger._get_component_dir(component)]
    else:
        comp_dirs = [d for d in logger.log_dir.iterdir() if d.is_dir()]
    
    for comp_dir in comp_dirs:
        for log_file in comp_dir.glob("*.json"):
            try:
                with open(log_file, 'r') as f:
                    content = f.read()
                    if query_lower in content.lower():
                        log_data = json.loads(content)
                        log_data["_filename"] = log_file.name
                        log_data["_component"] = comp_dir.name
                        matches.append(log_data)
                        
                        if len(matches) >= limit:
                            break
            except:
                continue
        
        if len(matches) >= limit:
            break
    
    # Display results
    if not matches:
        console.print(f"[yellow]No logs found containing '{query}'[/yellow]")
        return
    
    console.print(f"\n[green]Found {len(matches)} matches:[/green]\n")
    
    for log in matches:
        timestamp = log.get("timestamp", "Unknown")
        component = log.get("_component", "unknown")
        filename = log.get("_filename", "unknown")
        status = log.get("status", "unknown")
        
        # Find matching content
        all_text = json.dumps(log)
        idx = all_text.lower().find(query_lower)
        if idx >= 0:
            # Get surrounding context
            start = max(0, idx - 50)
            end = min(len(all_text), idx + len(query) + 50)
            context = all_text[start:end]
            if start > 0:
                context = "..." + context
            if end < len(all_text):
                context = context + "..."
            
            # Highlight the match
            context = context.replace(query, f"[bold yellow]{query}[/bold yellow]")
        else:
            context = "[dim]Match in content[/dim]"
        
        console.print(f"[cyan]{component}/{filename}[/cyan] [{status}]")
        console.print(f"  {context}")
        console.print()

if __name__ == "__main__":
    app()