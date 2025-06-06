# Interactive chat with the Manager
import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown

from agent.orchestrator.manager import Manager

app = typer.Typer()
console = Console()

@app.command()
def interactive():
    """Start an interactive chat session with the Manager"""
    
    console.print(Panel(
        "🤖 [bold blue]Cokeydex Manager[/bold blue]\n\n"
        "I'm your central orchestrator. I can:\n"
        "• Answer questions about the codebase\n" 
        "• Plan and coordinate complex tasks\n"
        "• Dispatch specialized agents when needed\n"
        "• Monitor costs and progress\n\n"
        "[dim]Type 'exit' to quit, 'status' for active tasks, 'cost' for usage[/dim]",
        title="Welcome"
    ))
    
    manager = Manager()
    
    while True:
        try:
            human_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            if human_input.lower() in ['exit', 'quit', 'bye']:
                console.print("👋 Goodbye!")
                break
            elif human_input.lower() == 'status':
                console.print(manager.get_active_tasks())
                continue
            elif human_input.lower() == 'cost':
                console.print(manager.get_cost_summary())
                continue
            
            # Get manager response
            response = manager.chat(human_input)
            
            # Display response
            console.print(f"\n[bold blue]Manager[/bold blue]: {response}")
            
        except KeyboardInterrupt:
            console.print("\n👋 Goodbye!")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")

@app.command()
def quick(message: str = typer.Argument(..., help="Message to send to manager")):
    """Send a quick message to the manager"""
    manager = Manager()
    response = manager.chat(message)
    console.print(response)

if __name__ == "__main__":
    app()