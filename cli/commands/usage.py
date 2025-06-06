# CLI command for checking LLM usage and costs
import typer
from typing import Optional
from datetime import date, timedelta
from rich.console import Console
from agent.models import UsageTracker

app = typer.Typer()
console = Console()

@app.command()
def report(days: int = typer.Option(7, "--days", "-d", help="Number of days to report")):
    """Show usage report for the last N days"""
    tracker = UsageTracker()
    report_text = tracker.get_usage_report(days=days)
    console.print(report_text)

@app.command()
def today():
    """Show today's usage and remaining budget"""
    tracker = UsageTracker()
    settings = tracker.settings
    
    today_cost = tracker.get_today_cost()
    remaining = settings.cost_cap_daily - today_cost
    
    console.print(f"Today's Usage: ${today_cost:.2f}")
    console.print(f"Daily Cap: ${settings.cost_cap_daily:.2f}")
    console.print(f"Remaining: ${remaining:.2f}")
    
    if remaining < settings.cost_cap_daily * 0.1:
        console.print("\n⚠️  Warning: Less than 10% of daily budget remaining!", style="yellow")

@app.command()
def task(task_id: str = typer.Argument(..., help="Task ID to check usage for")):
    """Show usage for a specific task"""
    tracker = UsageTracker()
    cost, input_tokens, output_tokens = tracker.get_usage_by_task(task_id)
    
    if cost == 0:
        console.print(f"No usage found for task {task_id}")
    else:
        console.print(f"Task {task_id} Usage:")
        console.print(f"  Cost: ${cost:.2f}")
        console.print(f"  Input tokens: {input_tokens:,}")
        console.print(f"  Output tokens: {output_tokens:,}")
        console.print(f"  Total tokens: {input_tokens + output_tokens:,}")

@app.command()
def model(
    model_id: str = typer.Argument(..., help="Model ID to check usage for"),
    days: int = typer.Option(7, "--days", "-d", help="Number of days to look back")
):
    """Show usage for a specific model"""
    tracker = UsageTracker()
    usage_by_date = tracker.get_usage_by_model(model_id, days=days)
    
    if not usage_by_date:
        console.print(f"No usage found for model {model_id}")
        return
    
    total_cost = 0
    total_input = 0
    total_output = 0
    
    console.print(f"\nUsage for {model_id} (last {days} days):")
    console.print("-" * 50)
    
    for date_str in sorted(usage_by_date.keys(), reverse=True):
        stats = usage_by_date[date_str]
        console.print(f"{date_str}: ${stats['cost']:.2f} ({stats['input_tokens']:,} in / {stats['output_tokens']:,} out)")
        total_cost += stats['cost']
        total_input += stats['input_tokens']
        total_output += stats['output_tokens']
    
    console.print("-" * 50)
    console.print(f"Total: ${total_cost:.2f} ({total_input:,} in / {total_output:,} out)")
    console.print(f"Daily average: ${total_cost/days:.2f}")

if __name__ == "__main__":
    app()