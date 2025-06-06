# Interactive chat with debugging for the OrchestratingManager
import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from rich.live import Live
from rich.layout import Layout
from rich.text import Text
import threading
import queue
from datetime import datetime

from agent.orchestrator.orchestrating_manager import OrchestratingManager
from agent.specialists.planner_agent import PlannerAgent
from agent.specialists.rag_agent import RAGSpecialist
from agent.specialists.executor_pool import ExecutorPool
from agent.communication.broker import MessageBroker

app = typer.Typer()
console = Console()

# Debug message queue for real-time updates
debug_queue = queue.Queue()

class DebugInterceptor:
    """Intercepts and logs broker messages for debugging"""
    def __init__(self, original_send):
        self.original_send = original_send
        
    def __call__(self, message, timeout=None):
        # Log the outgoing message
        debug_queue.put({
            "type": "message_sent",
            "time": datetime.now(),
            "sender": message.sender,
            "recipient": message.recipient,
            "action": message.payload.get("action", "unknown"),
            "message_id": message.message_id[:8] + "..."
        })
        
        # Call original method
        try:
            result = self.original_send(message, timeout)
            
            # Log the response
            if result:
                debug_queue.put({
                    "type": "message_received",
                    "time": datetime.now(),
                    "status": result.payload.get("status", "unknown"),
                    "message_id": message.message_id[:8] + "..."
                })
            else:
                debug_queue.put({
                    "type": "message_timeout",
                    "time": datetime.now(),
                    "message_id": message.message_id[:8] + "..."
                })
                
            return result
        except Exception as e:
            debug_queue.put({
                "type": "message_error",
                "time": datetime.now(),
                "error": str(e),
                "message_id": message.message_id[:8] + "..."
            })
            raise

def create_debug_layout():
    """Create a layout with chat and debug panels"""
    layout = Layout()
    layout.split_column(
        Layout(name="chat", size=20),
        Layout(name="debug", size=10)
    )
    return layout

def format_debug_messages(messages):
    """Format debug messages for display"""
    table = Table(title="🔍 Message Broker Debug", show_header=True, header_style="bold magenta")
    table.add_column("Time", style="dim", width=12)
    table.add_column("Type", style="cyan", width=15)
    table.add_column("Details", style="green")
    
    for msg in messages[-10:]:  # Show last 10 messages
        time_str = msg["time"].strftime("%H:%M:%S.%f")[:-3]
        
        if msg["type"] == "message_sent":
            details = f"{msg['sender']} → {msg['recipient']} [{msg['action']}] ID: {msg['message_id']}"
            table.add_row(time_str, "📤 SENT", details)
        elif msg["type"] == "message_received":
            details = f"Status: {msg['status']} ID: {msg['message_id']}"
            table.add_row(time_str, "📥 RECEIVED", details)
        elif msg["type"] == "message_timeout":
            details = f"⏱️ TIMEOUT ID: {msg['message_id']}"
            table.add_row(time_str, "⚠️ TIMEOUT", details, style="yellow")
        elif msg["type"] == "message_error":
            details = f"❌ {msg['error']} ID: {msg['message_id']}"
            table.add_row(time_str, "🔴 ERROR", details, style="red")
    
    return table

@app.command()
def interactive(
    model: str = typer.Option("gemini-2.5-flash-preview-05-20", help="Model to use for all agents"),
    debug: bool = typer.Option(True, help="Show debug output")
):
    """Start an interactive chat session with debugging"""
    
    console.print(Panel(
        f"🤖 [bold blue]Cokeydex Debug Chat[/bold blue]\n\n"
        f"Using model: [green]{model}[/green]\n"
        f"Debug mode: [yellow]{'ON' if debug else 'OFF'}[/yellow]\n\n"
        "I'm your central orchestrator with real-time debugging.\n"
        "Watch the message broker communication below!\n\n"
        "[dim]Commands: 'exit', 'status', 'broker' (broker stats)[/dim]",
        title="Welcome to Debug Mode"
    ))
    
    # Create agents with specified model
    console.print("\n[bold yellow]Creating agents...[/bold yellow]")
    
    # Create specialists first
    planner = PlannerAgent(model=model)
    console.print(f"✓ Planner created ({model})")
    
    rag = RAGSpecialist(model=model)
    console.print(f"✓ RAG Specialist created ({model})")
    
    executor = ExecutorPool(model=model)
    console.print(f"✓ Executor Pool created ({model})")
    
    # Create orchestrating manager with same model
    manager = OrchestratingManager(model=model)
    console.print(f"✓ Orchestrating Manager created ({model})\n")
    
    # Monkey-patch the broker for debugging
    if debug:
        broker = MessageBroker()
        broker.send_request = DebugInterceptor(broker.send_request)
    
    # Store debug messages
    debug_messages = []
    
    while True:
        try:
            # Get debug messages without blocking
            while not debug_queue.empty():
                debug_messages.append(debug_queue.get_nowait())
            
            # Show debug panel if enabled
            if debug and debug_messages:
                console.print(format_debug_messages(debug_messages))
            
            human_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            if human_input.lower() in ['exit', 'quit', 'bye']:
                console.print("👋 Goodbye!")
                break
            elif human_input.lower() == 'status':
                status = manager.get_system_status()
                console.print(Panel(
                    f"Active agents: {len(status['manager_status']['registered_agents'])}\n"
                    f"Session duration: {status['manager_status']['session_duration']:.1f}s\n"
                    f"Tasks completed: {len([t for t in status['task_progress'].values() if t['status'] == 'completed'])}",
                    title="📊 System Status"
                ))
                continue
            elif human_input.lower() == 'broker':
                broker = MessageBroker()
                stats = broker.get_stats()
                console.print(Panel(
                    f"Messages sent: {stats['messages_sent']}\n"
                    f"Messages delivered: {stats['messages_delivered']}\n"
                    f"Messages failed: {stats['messages_failed']}\n"
                    f"Registered agents: {', '.join(stats['registered_agents'])}",
                    title="📬 Broker Stats"
                ))
                continue
            
            # Clear debug messages for new request
            debug_messages.clear()
            
            # Get manager response
            console.print("\n[dim]Processing...[/dim]")
            response = manager.chat(human_input)
            
            # Get final debug messages
            while not debug_queue.empty():
                debug_messages.append(debug_queue.get_nowait())
            
            # Show final debug output
            if debug and debug_messages:
                console.print("\n")
                console.print(format_debug_messages(debug_messages))
            
            # Display response
            console.print(f"\n[bold blue]Manager[/bold blue]:\n{response}")
            
            # Show any failed tasks
            if hasattr(manager, 'task_progress'):
                failed_tasks = [
                    (tid, tinfo) for tid, tinfo in manager.task_progress.items() 
                    if tinfo.get('status') == 'failed'
                ]
                if failed_tasks:
                    console.print("\n[red]⚠️ Failed Tasks:[/red]")
                    for task_id, task_info in failed_tasks:
                        console.print(f"  - {task_id}: {task_info.get('error', 'Unknown error')}")
            
        except KeyboardInterrupt:
            console.print("\n👋 Goodbye!")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            import traceback
            if debug:
                console.print(traceback.format_exc())

@app.command()
def quick(
    message: str = typer.Argument(..., help="Message to send to manager"),
    model: str = typer.Option("gemini-2.5-flash-preview-05-20", help="Model to use")
):
    """Send a quick message with debugging"""
    # Create agents
    planner = PlannerAgent(model=model)
    rag = RAGSpecialist(model=model)
    executor = ExecutorPool(model=model)
    manager = OrchestratingManager(model=model)
    
    response = manager.chat(message)
    console.print(response)

if __name__ == "__main__":
    app()