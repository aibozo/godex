# CLI commands for monitoring broker communication
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from datetime import datetime

from agent.communication.monitor import get_message_monitor, MessageStatus

app = typer.Typer()
console = Console()

@app.command()
def status():
    """Show current broker monitoring status"""
    monitor = get_message_monitor()
    
    if not monitor.traces:
        console.print("[yellow]No messages tracked yet[/yellow]")
        return
    
    # Create summary table
    table = Table(title="Broker Message Summary", show_header=True)
    table.add_column("Status", style="cyan")
    table.add_column("Count", style="white")
    
    # Count by status
    status_counts = {}
    for trace in monitor.traces.values():
        status = trace.get_status()
        status_counts[status] = status_counts.get(status, 0) + 1
    
    # Add rows
    for status in MessageStatus:
        count = status_counts.get(status, 0)
        if count > 0:
            style = {
                MessageStatus.COMPLETED: "green",
                MessageStatus.FAILED: "red",
                MessageStatus.TIMEOUT: "yellow",
                MessageStatus.NO_HANDLER: "red",
                MessageStatus.PROCESSING: "blue"
            }.get(status, "white")
            
            table.add_row(
                Text(status.value, style=style),
                str(count)
            )
    
    console.print(table)
    
    # Show recent failures
    failures = monitor.get_recent_failures(5)
    if failures:
        console.print("\n[bold red]Recent Failures:[/bold red]")
        for trace in failures:
            last_event = trace.events[-1] if trace.events else None
            console.print(f"\n• Message: {trace.message_id[:8]}...")
            console.print(f"  From: {trace.sender} → {trace.recipient}")
            console.print(f"  Type: {trace.message_type}")
            if last_event:
                console.print(f"  Status: [red]{last_event.status.value}[/red]")
                console.print(f"  Details: {last_event.details}")
                if last_event.error:
                    console.print(f"  Error: [red]{last_event.error}[/red]")

@app.command()
def trace(message_id: str):
    """Show detailed trace for a specific message"""
    monitor = get_message_monitor()
    trace = monitor.get_trace(message_id)
    
    if not trace:
        # Try partial match
        for mid, t in monitor.traces.items():
            if mid.startswith(message_id):
                trace = t
                break
    
    if not trace:
        console.print(f"[red]No trace found for message ID: {message_id}[/red]")
        return
    
    # Show message info
    panel = Panel(
        f"ID: {trace.message_id}\n"
        f"From: {trace.sender} → {trace.recipient}\n"
        f"Type: {trace.message_type}\n"
        f"Created: {trace.created_at.strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"Duration: {trace.get_duration():.2f}s\n"
        f"Status: {trace.get_status().value}",
        title="Message Details",
        border_style="cyan"
    )
    console.print(panel)
    
    # Show event timeline
    console.print("\n[bold]Event Timeline:[/bold]")
    
    for event in trace.events:
        # Format timestamp
        time_str = event.timestamp.strftime("%H:%M:%S.%f")[:-3]
        
        # Status color
        status_color = {
            MessageStatus.SENT: "blue",
            MessageStatus.RECEIVED: "green", 
            MessageStatus.PROCESSING: "yellow",
            MessageStatus.COMPLETED: "green",
            MessageStatus.FAILED: "red",
            MessageStatus.TIMEOUT: "red",
            MessageStatus.NO_HANDLER: "red"
        }.get(event.status, "white")
        
        # Print event
        console.print(
            f"  {time_str} [{status_color}]{event.status.value:12}[/{status_color}] {event.details}"
        )
        
        if event.error:
            console.print(f"              [red]Error: {event.error}[/red]")
        
        if event.metadata:
            for key, value in event.metadata.items():
                console.print(f"              {key}: {value}")

@app.command()
def clear():
    """Clear all broker monitoring data"""
    monitor = get_message_monitor()
    count = len(monitor.traces)
    monitor.clear()
    console.print(f"[green]Cleared {count} message traces[/green]")

@app.command()
def live():
    """Show live message flow (press Ctrl+C to stop)"""
    import time
    
    monitor = get_message_monitor()
    console.print("[cyan]Monitoring broker messages... (Press Ctrl+C to stop)[/cyan]\n")
    
    # Enable console output
    monitor.enable_console_output = True
    
    try:
        # Keep showing updates
        last_count = 0
        while True:
            current_count = len(monitor.traces)
            if current_count > last_count:
                # New messages, show summary
                monitor.print_summary()
                last_count = current_count
            time.sleep(0.5)
    except KeyboardInterrupt:
        console.print("\n[yellow]Stopped monitoring[/yellow]")
        monitor.print_summary()

if __name__ == "__main__":
    app()