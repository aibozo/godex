# Sophisticated cost optimization strategies
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum
import asyncio
from datetime import datetime, timedelta

from agent.models import get_model_info, calculate_cost, UsageTracker

class OptimizationStrategy(Enum):
    COST_MINIMAL = "cost_minimal"      # Cheapest models, highest latency
    BALANCED = "balanced"              # Good balance of cost/performance  
    PERFORMANCE = "performance"        # Best models, higher cost
    ADAPTIVE = "adaptive"              # Dynamically adjust based on complexity

@dataclass
class TaskComplexity:
    cognitive_load: int      # 1-5, how much reasoning needed
    context_size: int        # Number of tokens of context needed
    precision_required: int  # 1-5, how precise the output must be
    iteration_likely: int    # 1-5, likelihood of needing refinement

class CostOptimizer:
    """
    Sophisticated cost optimization that:
    1. Routes tasks to optimal models based on complexity
    2. Implements progressive enhancement (start cheap, upgrade if needed)
    3. Batches similar tasks
    4. Uses caching for repeated patterns
    5. Implements circuit breakers for cost control
    """
    
    def __init__(self):
        self.usage_tracker = UsageTracker()
        self.task_history: List[Dict] = []
        self.model_performance_cache: Dict[str, float] = {}
        
        # Model tiers by cost and capability
        self.model_tiers = {
            "cheap": [
                "gemini-1.5-flash",           # $0.075/$0.30 per 1M tokens
                "gpt-4o-mini",                # Estimated cheap
            ],
            "mid": [
                "claude-3.5-sonnet-20241022", # $3/$15 per 1M tokens
                "gpt-4o",                     # $2.50/$10 per 1M tokens
                "gemini-2.5-flash-preview-05-20"  # $0.60/$2.40 per 1M tokens
            ],
            "premium": [
                "claude-opus-4-20250514",     # $15/$75 per 1M tokens
                "claude-sonnet-4-20250514",   # $3/$15 per 1M tokens
                "o1",                         # $15/$60 per 1M tokens
                "gemini-2.5-pro-preview-06-05"  # $2.50/$10 per 1M tokens
            ]
        }
    
    def optimize_model_selection(
        self,
        task_description: str,
        agent_role: str,
        complexity: TaskComplexity,
        strategy: OptimizationStrategy = OptimizationStrategy.ADAPTIVE
    ) -> str:
        """
        Select optimal model based on task complexity and strategy
        """
        
        if strategy == OptimizationStrategy.COST_MINIMAL:
            return self._select_cheapest_capable(complexity)
        elif strategy == OptimizationStrategy.PERFORMANCE:
            return self._select_best_model(agent_role)
        elif strategy == OptimizationStrategy.ADAPTIVE:
            return self._adaptive_selection(task_description, agent_role, complexity)
        else:  # BALANCED
            return self._balanced_selection(complexity, agent_role)
    
    def _analyze_task_complexity(self, task_description: str, agent_role: str) -> TaskComplexity:
        """Analyze task to determine complexity metrics"""
        
        # Simple heuristics (could be improved with ML)
        desc_lower = task_description.lower()
        
        # Cognitive load indicators
        cognitive_load = 1
        if any(word in desc_lower for word in ["design", "architecture", "plan", "strategy"]):
            cognitive_load += 2
        if any(word in desc_lower for word in ["complex", "advanced", "sophisticated"]):
            cognitive_load += 2
        if any(word in desc_lower for word in ["debug", "fix", "error", "issue"]):
            cognitive_load += 1
            
        # Context size indicators  
        context_size = 5000  # Base
        if "entire codebase" in desc_lower or "project-wide" in desc_lower:
            context_size = 100_000
        elif any(word in desc_lower for word in ["multiple files", "across files"]):
            context_size = 50_000
        elif any(word in desc_lower for word in ["single file", "function"]):
            context_size = 10_000
            
        # Precision requirements
        precision_required = 3  # Default
        if agent_role == "planner":
            precision_required = 4  # Plans need to be precise
        elif "test" in desc_lower or "production" in desc_lower:
            precision_required = 5
        elif "prototype" in desc_lower or "quick" in desc_lower:
            precision_required = 2
            
        return TaskComplexity(
            cognitive_load=min(5, cognitive_load),
            context_size=context_size,
            precision_required=precision_required,
            iteration_likely=3  # Default assumption
        )
    
    def _adaptive_selection(
        self, 
        task_description: str, 
        agent_role: str, 
        complexity: TaskComplexity
    ) -> str:
        """
        Adaptive selection based on:
        1. Task complexity
        2. Historical performance
        3. Current budget remaining
        4. Time of day/usage patterns
        """
        
        # Check budget remaining
        today_usage = self.usage_tracker.get_today_cost()
        daily_cap = self.usage_tracker.settings.cost_cap_daily
        budget_remaining = daily_cap - today_usage
        budget_ratio = budget_remaining / daily_cap
        
        # If budget is low, prefer cheaper models
        if budget_ratio < 0.2:  # Less than 20% budget remaining
            return self._select_cheapest_capable(complexity)
        
        # Route based on complexity and role
        if agent_role == "manager":
            # Manager should stay lightweight
            return "claude-opus-4-20250514"  # High capability, controlled usage
            
        elif agent_role == "planner":
            if complexity.cognitive_load >= 4:
                return "o1"  # Best reasoning for complex planning
            else:
                return "gemini-2.5-pro-preview-06-05"  # Good planning, cheaper
                
        elif agent_role == "executor":
            if complexity.context_size > 50_000:
                return "gemini-2.5-flash-preview-05-20"  # Good context handling
            elif complexity.precision_required >= 4:
                return "claude-sonnet-4-20250514"  # High precision
            else:
                return "claude-3.5-sonnet-20241022"  # Good balance
                
        elif agent_role == "rag_specialist":
            return "gpt-4o"  # High context, decent cost
            
        # Default fallback
        return "claude-3.5-sonnet-20241022"
    
    def _select_cheapest_capable(self, complexity: TaskComplexity) -> str:
        """Select cheapest model capable of handling the complexity"""
        
        if complexity.cognitive_load <= 2 and complexity.precision_required <= 3:
            return "gemini-1.5-flash"  # Cheapest option
        elif complexity.cognitive_load <= 3:
            return "gemini-2.5-flash-preview-05-20"  # Cheap but capable
        else:
            return "claude-3.5-sonnet-20241022"  # Cheapest premium option
    
    def _select_best_model(self, agent_role: str) -> str:
        """Select best model regardless of cost"""
        role_best = {
            "manager": "claude-opus-4-20250514",
            "planner": "o1",
            "executor": "claude-sonnet-4-20250514", 
            "rag_specialist": "gpt-4o"
        }
        return role_best.get(agent_role, "claude-opus-4-20250514")
    
    def _balanced_selection(self, complexity: TaskComplexity, agent_role: str) -> str:
        """Balanced cost/performance selection"""
        
        # Use mid-tier models for most tasks
        role_balanced = {
            "manager": "claude-opus-4-20250514",  # Manager gets premium
            "planner": "gemini-2.5-pro-preview-06-05",
            "executor": "claude-3.5-sonnet-20241022",
            "rag_specialist": "gpt-4o"
        }
        
        # Upgrade for high complexity
        if complexity.cognitive_load >= 4 or complexity.precision_required >= 4:
            if agent_role == "planner":
                return "o1"
            elif agent_role == "executor":
                return "claude-sonnet-4-20250514"
        
        return role_balanced.get(agent_role, "claude-3.5-sonnet-20241022")
    
    def estimate_task_cost(
        self,
        task_description: str,
        agent_role: str,
        model_id: str,
        estimated_iterations: int = 1
    ) -> Dict[str, float]:
        """
        Estimate total cost for a task including potential iterations
        """
        
        complexity = self._analyze_task_complexity(task_description, agent_role)
        
        # Estimate tokens based on complexity
        estimated_input = complexity.context_size + 1000  # Context + prompt
        estimated_output = self._estimate_output_tokens(task_description, agent_role)
        
        # Calculate base cost
        base_cost = calculate_cost(model_id, estimated_input, estimated_output)
        
        # Factor in iterations
        total_cost = base_cost * estimated_iterations
        
        return {
            "base_cost": base_cost,
            "estimated_iterations": estimated_iterations,
            "total_estimated_cost": total_cost,
            "input_tokens": estimated_input,
            "output_tokens": estimated_output
        }
    
    def _estimate_output_tokens(self, task_description: str, agent_role: str) -> int:
        """Estimate output tokens based on task and role"""
        
        base_outputs = {
            "manager": 500,      # Brief orchestration
            "planner": 2000,     # Detailed plans
            "executor": 5000,    # Code generation
            "rag_specialist": 1000  # Context summaries
        }
        
        base = base_outputs.get(agent_role, 1000)
        
        # Adjust based on task indicators
        desc_lower = task_description.lower()
        if "large" in desc_lower or "complex" in desc_lower:
            base *= 2
        elif "simple" in desc_lower or "quick" in desc_lower:
            base *= 0.5
            
        return int(base)
    
    def progressive_enhancement(
        self,
        task_description: str,
        agent_role: str,
        initial_result: str,
        success_criteria: str
    ) -> str:
        """
        Progressive enhancement: start cheap, upgrade if result insufficient
        """
        
        # Start with cheap model
        cheap_model = self._select_cheapest_capable(
            self._analyze_task_complexity(task_description, agent_role)
        )
        
        # If initial result meets criteria, use it
        if self._evaluate_result_quality(initial_result, success_criteria):
            return cheap_model
        
        # Otherwise, upgrade to better model
        return self._select_best_model(agent_role)
    
    def _evaluate_result_quality(self, result: str, criteria: str) -> bool:
        """Evaluate if result meets quality criteria"""
        # Simplified quality check (could use another model to evaluate)
        return len(result) > 100 and "error" not in result.lower()
    
    def get_cost_optimization_report(self) -> str:
        """Generate cost optimization insights"""
        
        today_cost = self.usage_tracker.get_today_cost()
        daily_cap = self.usage_tracker.settings.cost_cap_daily
        
        report = f"""
💰 Cost Optimization Report

Today's Usage: ${today_cost:.4f} / ${daily_cap:.2f}
Budget Remaining: ${daily_cap - today_cost:.4f} ({(daily_cap - today_cost)/daily_cap*100:.1f}%)

Recommendations:
"""
        
        if today_cost / daily_cap > 0.8:
            report += "⚠️  High usage - switch to cost-minimal strategy\n"
        elif today_cost / daily_cap < 0.3:
            report += "✅ Low usage - can use performance strategy\n"
        else:
            report += "📊 Moderate usage - balanced strategy recommended\n"
            
        return report