# Interactive chat with enhanced LLM-based orchestration
import typer
from rich.console import Console
from rich.prompt import Prompt
from rich.panel import Panel
from rich.markdown import Markdown
import time

from agent.orchestrator.llm_orchestrator import LLMOrchestratingManager
from agent.communication.broker import MessageBroker

# Import the enhanced agents
from agent.specialists.enhanced_planner import EnhancedPlannerAgent
from agent.specialists.enhanced_rag import EnhancedRAGSpecialist
from agent.specialists.executor_pool import ExecutorPool

app = typer.Typer()
console = Console()

def start_enhanced_agents():
    """Start all enhanced specialized agents"""
    console.print("[dim]Starting enhanced agents...[/dim]")
    
    # Create message broker instance
    broker = MessageBroker()
    
    # Start specialized agents
    agents = []
    
    try:
        # Start Enhanced Planner
        planner = EnhancedPlannerAgent()
        console.print("✓ Enhanced Planner Agent started")
        agents.append(planner)
        
        # Start Enhanced RAG Specialist with Gemini 2.5 Flash
        rag = EnhancedRAGSpecialist(model="gemini-2.5-flash-preview-05-20")
        console.print("✓ Enhanced RAG Specialist started (Gemini 2.5 Flash)")
        agents.append(rag)
        
        # Start Executor Pool (using existing one for now)
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
    """Start an interactive chat session with enhanced orchestration"""
    
    console.print(Panel(
        "🚀 [bold cyan]Cokeydex Enhanced Orchestrator[/bold cyan]\n\n"
        "Advanced features:\n"
        "• [green]Smart Planning[/green]: Context-aware task breakdown with codebase analysis\n" 
        "• [blue]Intelligent RAG[/blue]: LLM-powered search synthesis and pattern recognition\n"
        "• [yellow]Dynamic Workflows[/yellow]: Adaptive orchestration based on context\n"
        "• [magenta]Failure Recovery[/magenta]: Automatic replanning on task failures\n\n"
        "[dim]Type 'exit' to quit, 'status' for system status[/dim]",
        title="Enhanced Multi-Agent System"
    ))
    
    # Start agents first
    try:
        agents, broker = start_enhanced_agents()
    except Exception as e:
        console.print(f"[red]Failed to start agents: {e}[/red]")
        return
    
    # Create the LLM orchestrating manager
    manager = LLMOrchestratingManager()
    
    # Register agents with manager
    manager.register_agent("planner")
    manager.register_agent("rag_specialist")
    manager.register_agent("executor")
    
    console.print("\n[green]✓ Enhanced system ready![/green]\n")
    
    # Show examples
    console.print(Panel(
        "Example requests you can try:\n"
        "• 'Analyze the codebase structure and suggest improvements'\n"
        "• 'Create a new feature for user authentication'\n"
        "• 'Refactor the memory management system'\n"
        "• 'Search for all error handling patterns in the project'\n"
        "• 'Build a comprehensive test suite for the agent system'",
        title="Try These Examples",
        border_style="dim"
    ))
    
    while True:
        try:
            human_input = Prompt.ask("\n[bold green]You[/bold green]")
            
            if human_input.lower() in ['exit', 'quit', 'bye']:
                console.print("👋 Goodbye!")
                break
            elif human_input.lower() == 'status':
                status = manager.get_system_status()
                
                # Also get agent statuses
                agent_statuses = {}
                for agent_type in ["planner", "rag_specialist", "executor"]:
                    agent_status = manager._get_agent_status({"agent_type": agent_type})
                    if agent_status.get("status") != "error":
                        agent_statuses[agent_type] = agent_status
                
                console.print(Panel(
                    f"[bold]Manager Status[/bold]\n"
                    f"Session Duration: {status['manager_status']['session_duration']:.1f}s\n"
                    f"Total Requests: {status['manager_status']['total_requests']}\n"
                    f"Tasks Completed: {status['manager_status']['tasks_completed']}\n"
                    f"Tasks Failed: {status['manager_status']['tasks_failed']}\n"
                    f"Active Plan: {'Yes' if status['manager_status']['active_plan'] else 'No'}\n\n"
                    f"[bold]Agent Status[/bold]\n" +
                    "\n".join([
                        f"{agent.title()}: {agent_statuses.get(agent, {}).get('status', 'Unknown')}"
                        for agent in ["planner", "rag_specialist", "executor"]
                    ]),
                    title="System Status"
                ))
                continue
            
            # Show thinking indicator with progress
            with console.status("[bold yellow]Orchestrating agents...[/bold yellow]", spinner="dots"):
                start_time = time.time()
                response = manager.chat(human_input)
                elapsed = time.time() - start_time
            
            # Display response with markdown rendering
            console.print(f"\n[bold blue]Manager[/bold blue] [dim](responded in {elapsed:.1f}s)[/dim]:")
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
def demo():
    """Run a demonstration of enhanced capabilities"""
    
    console.print(Panel(
        "🎭 [bold]Enhanced Orchestration Demo[/bold]\n\n"
        "This demo will showcase:\n"
        "1. Codebase analysis with pattern recognition\n"
        "2. Context-aware planning\n"
        "3. Intelligent task decomposition",
        title="Demo Mode"
    ))
    
    # Start agents
    try:
        agents, broker = start_enhanced_agents()
    except Exception as e:
        console.print(f"[red]Failed to start agents: {e}[/red]")
        return
    
    # Create manager
    manager = LLMOrchestratingManager()
    manager.register_agent("planner")
    manager.register_agent("rag_specialist")
    manager.register_agent("executor")
    
    # Demo queries
    demo_queries = [
        "Analyze the agent communication system and identify areas for improvement",
        "Create a plan to add comprehensive error handling to all agents",
        "Search for all tool implementations and summarize their patterns"
    ]
    
    for i, query in enumerate(demo_queries, 1):
        console.print(f"\n[bold cyan]Demo {i}:[/bold cyan] {query}")
        
        with console.status("[yellow]Processing...[/yellow]"):
            response = manager.chat(query)
        
        console.print(f"\n[bold blue]Response:[/bold blue]")
        console.print(Markdown(response))
        
        if i < len(demo_queries):
            console.print("\n[dim]Press Enter to continue...[/dim]")
            input()

if __name__ == "__main__":
    app()