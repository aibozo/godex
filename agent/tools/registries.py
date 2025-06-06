"""
Tool registry system for agent-specific tool permissions.

Each agent type has a specific set of tools they're allowed to use.
This enforces the principle of least privilege and role separation.
"""

from typing import List, Dict, Set


# Tool definitions by agent type
MANAGER_TOOLS = [
    "create_project",
    "create_plan", 
    "start_task",
    "get_task_status",
    "get_context_summary",
    "update_conversation",
    "cost_monitor",
    "delegate_to_planner",
    "start_task_execution", 
    "get_progress_summary",
    # Agent communication tools
    "message_planner",
    "message_rag",
    "message_executor",
    "get_agent_status",
    "coordinate_agents"
]

PLANNER_TOOLS = [
    "query_rag",
    "analyze_codebase",
    "create_task_breakdown",
    "validate_plan",
    "refine_scope", 
    "estimate_resources",
    "request_rag_context",
    "analyze_task_dependencies",
    "estimate_implementation_effort",
    "validate_plan_feasibility"
]

RAG_TOOLS = [
    "hybrid_search",
    "rank_chunks", 
    "build_context",
    "update_index",
    "extract_patterns",
    "summarize_codebase",
    "enhanced_hybrid_search",
    "context_synthesis",
    "pattern_extraction", 
    "incremental_index_update"
]

EXECUTOR_TOOLS = [
    "read_file",
    "write_diff",
    "run_tests", 
    "static_analyze",
    "git_operations",
    "run_command",
    "validate_implementation",
    "guided_implementation",
    "test_driven_development",
    "incremental_validation",
    "rollback_on_failure",
    "grep",
    "vector_search"
]

# Additional existing tools that can be shared
SHARED_TOOLS = [
    "read_file",  # Basic file reading is generally safe
    "grep",       # Search is generally safe
]

# Agent type to tools mapping
AGENT_TOOL_REGISTRY: Dict[str, List[str]] = {
    "manager": MANAGER_TOOLS + ["read_file", "grep"],  # Manager gets basic read access
    "planner": PLANNER_TOOLS + ["read_file", "grep"], # Planner gets basic read access  
    "rag": RAG_TOOLS + ["read_file", "grep"],         # RAG gets read and search
    "executor": EXECUTOR_TOOLS,                       # Executor gets full tool access
    "rag_specialist": RAG_TOOLS + ["read_file", "grep"], # Alias for rag
}


def get_agent_tools(agent_type: str) -> List[str]:
    """
    Get the list of tools allowed for a specific agent type.
    
    Args:
        agent_type: The agent component name (manager, planner, rag, executor)
        
    Returns:
        List of tool names the agent is allowed to use
        
    Raises:
        ValueError: If agent_type is not recognized
    """
    if agent_type not in AGENT_TOOL_REGISTRY:
        raise ValueError(f"Unknown agent type: {agent_type}. Valid types: {list(AGENT_TOOL_REGISTRY.keys())}")
    
    return AGENT_TOOL_REGISTRY[agent_type].copy()


def is_tool_allowed(agent_type: str, tool_name: str) -> bool:
    """
    Check if a specific tool is allowed for an agent type.
    
    Args:
        agent_type: The agent component name
        tool_name: The tool to check
        
    Returns:
        True if tool is allowed, False otherwise
    """
    try:
        allowed_tools = get_agent_tools(agent_type)
        return tool_name in allowed_tools
    except ValueError:
        return False


def add_tool_to_agent(agent_type: str, tool_name: str) -> None:
    """
    Add a tool to an agent's allowed tools list.
    
    Args:
        agent_type: The agent component name
        tool_name: The tool to add
        
    Raises:
        ValueError: If agent_type is not recognized
    """
    if agent_type not in AGENT_TOOL_REGISTRY:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    if tool_name not in AGENT_TOOL_REGISTRY[agent_type]:
        AGENT_TOOL_REGISTRY[agent_type].append(tool_name)


def remove_tool_from_agent(agent_type: str, tool_name: str) -> None:
    """
    Remove a tool from an agent's allowed tools list.
    
    Args:
        agent_type: The agent component name
        tool_name: The tool to remove
        
    Raises:
        ValueError: If agent_type is not recognized
    """
    if agent_type not in AGENT_TOOL_REGISTRY:
        raise ValueError(f"Unknown agent type: {agent_type}")
    
    if tool_name in AGENT_TOOL_REGISTRY[agent_type]:
        AGENT_TOOL_REGISTRY[agent_type].remove(tool_name)


def get_all_tools() -> Set[str]:
    """
    Get a set of all tools used across all agent types.
    
    Returns:
        Set of all tool names
    """
    all_tools = set()
    for tools in AGENT_TOOL_REGISTRY.values():
        all_tools.update(tools)
    return all_tools


def get_tool_usage_by_agent() -> Dict[str, List[str]]:
    """
    Get a summary of which agents can use each tool.
    
    Returns:
        Dict mapping tool names to list of agent types that can use them
    """
    tool_usage = {}
    
    for agent_type, tools in AGENT_TOOL_REGISTRY.items():
        for tool in tools:
            if tool not in tool_usage:
                tool_usage[tool] = []
            tool_usage[tool].append(agent_type)
    
    return tool_usage


def validate_tool_registry() -> List[str]:
    """
    Validate the tool registry for any issues.
    
    Returns:
        List of validation warnings/errors
    """
    issues = []
    
    # Check for duplicate tools in SHARED_TOOLS
    duplicates_in_shared = set(SHARED_TOOLS) & set().union(*[
        set(tools) for agent_type, tools in AGENT_TOOL_REGISTRY.items()
    ])
    
    if duplicates_in_shared:
        issues.append(f"Tools in SHARED_TOOLS are already in agent registries: {duplicates_in_shared}")
    
    # Check for empty tool lists
    for agent_type, tools in AGENT_TOOL_REGISTRY.items():
        if not tools:
            issues.append(f"Agent type '{agent_type}' has no tools assigned")
    
    return issues


# Registry metadata
REGISTRY_INFO = {
    "version": "1.0.0",
    "last_updated": "2024-01-01",
    "total_agents": len(AGENT_TOOL_REGISTRY),
    "total_unique_tools": len(get_all_tools()),
}


if __name__ == "__main__":
    # Quick test/demo of the registry
    print("=== Cokeydx Tool Registry ===")
    print(f"Registry Info: {REGISTRY_INFO}")
    print()
    
    for agent_type in AGENT_TOOL_REGISTRY.keys():
        tools = get_agent_tools(agent_type)
        print(f"{agent_type.upper()} ({len(tools)} tools):")
        for tool in sorted(tools):
            print(f"  - {tool}")
        print()
    
    # Validation
    issues = validate_tool_registry()
    if issues:
        print("VALIDATION ISSUES:")
        for issue in issues:
            print(f"  ⚠️  {issue}")
    else:
        print("✅ Tool registry validation passed")