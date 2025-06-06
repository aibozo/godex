# Interactive chat with the LLM-based Orchestrating Manager
import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown
import asyncio
import time

from agent.orchestrator.llm_orchestrator import LLMOrchestratingManager
from agent.communication.broker import MessageBroker

# Import the specialized agents
from agent.specialists.planner_agent import PlannerAgent
from agent.specialists.rag_agent import RAGSpecialist
from agent.specialists.executor_pool import ExecutorPool

app = typer.Typer()
console = Console()

def start_agents():
    """Start all specialized agents"""
    console.print("[dim]Starting specialized agents...[/dim]")
    
    # Create message broker instance
    broker = MessageBroker()
    
    # Start specialized agents
    agents = []
    
    try:
        # Start Planner
        planner = PlannerAgent()
        console.print("✓ Planner Agent started")
        agents.append(planner)
        
        # Start RAG Specialist with Gemini 2.5 Flash
        rag = RAGSpecialist(model="gemini-2.5-flash-preview-05-20")
        console.print("✓ RAG Specialist started (Gemini 2.5 Flash)")
        agents.append(rag)
        
        # Start Executor Pool
        executor = ExecutorPool()
        console.print("✓ Executor Pool started")
        agents.append(executor)
        
        # Give agents time to register
        time.sleep(0.5)
        
        return agents, broker
        
    except Exception as e:
        console.print(f"[red]Error starting agents: {e}[/red]")
        raise

@app.command()
def interactive():
    """Start an interactive chat session with the LLM-based Orchestrating Manager"""
    
    console.print(Panel(
        "🤖 [bold blue]Cokeydex LLM Orchestrator[/bold blue]\n\n"
        "I'm your AI-powered orchestrator. I can:\n"
        "• Understand your requests and dynamically coordinate agents\n" 
        "• Create detailed plans using the Planning Agent\n"
        "• Search and analyze code using the RAG Specialist\n"
        "• Implement solutions using the Executor Pool\n"
        "• Handle complex multi-step workflows intelligently\n\n"
        "[dim]Type 'exit' to quit, 'status' for system status[/dim]",
        title="Welcome to LLM-based Orchestration"
    ))
    
    # Start agents first
    try:
        agents, broker = start_agents()
    except Exception as e:
        console.print(f"[red]Failed to start agents: {e}[/red]")
        return
    
    # Create the LLM orchestrating manager
    manager = LLMOrchestratingManager()
    
    # Register agents with manager
    manager.register_agent("planner")
    manager.register_agent("rag_specialist")
    manager.register_agent("executor")
    
    console.print("\n[green]✓ All systems ready![/green]\n")
    
    while True:
        try:
            human_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            if human_input.lower() in ['exit', 'quit', 'bye']:
                console.print("👋 Goodbye!")
                break
            elif human_input.lower() == 'status':
                status = manager.get_system_status()
                console.print(Panel(
                    f"Session Duration: {status['manager_status']['session_duration']:.1f}s\n"
                    f"Total Requests: {status['manager_status']['total_requests']}\n"
                    f"Registered Agents: {', '.join(status['manager_status']['registered_agents'])}\n"
                    f"Tasks Completed: {status['manager_status']['tasks_completed']}\n"
                    f"Tasks Failed: {status['manager_status']['tasks_failed']}\n"
                    f"Active Plan: {'Yes' if status['manager_status']['active_plan'] else 'No'}",
                    title="System Status"
                ))
                continue
            
            # Show thinking indicator
            with console.status("[bold yellow]Thinking...[/bold yellow]"):
                response = manager.chat(human_input)
            
            # Display response with markdown rendering
            console.print("\n[bold blue]Manager[/bold blue]:")
            console.print(Markdown(response))
            
        except KeyboardInterrupt:
            console.print("\n👋 Goodbye!")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")
            import traceback
            if console.is_terminal:
                traceback.print_exc()

@app.command()
def quick(message: str = typer.Argument(..., help="Message to send to manager")):
    """Send a quick message to the LLM orchestrating manager"""
    
    # Start agents
    try:
        agents, broker = start_agents()
    except Exception as e:
        console.print(f"[red]Failed to start agents: {e}[/red]")
        return
    
    # Create manager and register agents
    manager = LLMOrchestratingManager()
    manager.register_agent("planner")
    manager.register_agent("rag_specialist")
    manager.register_agent("executor")
    
    # Get response
    with console.status("[bold yellow]Processing...[/bold yellow]"):
        response = manager.chat(message)
    
    console.print(Markdown(response))

if __name__ == "__main__":
    app()