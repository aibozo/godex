# Intelligent context management and optimization
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum

from agent.retrieval.orchestrator import HybridRetriever
from agent.llm import LLMClient

class ContextType(Enum):
    CODE_IMPLEMENTATION = "code_implementation"
    API_REFERENCE = "api_reference" 
    EXAMPLES = "examples"
    DOCUMENTATION = "documentation"
    TESTS = "tests"

@dataclass
class ContextChunk:
    content: str
    file_path: str
    context_type: ContextType
    relevance_score: float
    token_count: int
    dependencies: List[str] = None

class ContextOptimizer:
    """
    Intelligently manages context allocation across agents:
    - RAG specialist gathers candidates
    - Context optimizer ranks and filters
    - Delivers precisely what each agent needs
    """
    
    def __init__(self):
        self.retriever = HybridRetriever()
        # Use GPT-4.1 for context analysis (high context, cheaper)
        self.rag_llm = LLMClient("gpt-4o", component="rag_specialist")  # Fallback until 4.1
    
    def build_context_for_agent(
        self, 
        task_description: str,
        agent_role: str,
        budget_tokens: int,
        task_type: str = "coding"
    ) -> Dict[str, any]:
        """
        Build optimized context for a specific agent and task
        
        Returns:
            {
                "chunks": [ContextChunk],
                "total_tokens": int,
                "context_summary": str,
                "key_files": [str],
                "missing_info": [str]
            }
        """
        
        # Stage 1: Broad retrieval
        raw_chunks = self.retriever.fetch_context(task_description, top_n=20)
        
        # Stage 2: Intelligent filtering and ranking
        context_chunks = self._analyze_and_rank_chunks(
            raw_chunks, 
            task_description,
            agent_role,
            task_type
        )
        
        # Stage 3: Budget allocation
        selected_chunks = self._allocate_context_budget(
            context_chunks,
            budget_tokens,
            agent_role
        )
        
        # Stage 4: Build final context package
        return self._package_context(selected_chunks, task_description)
    
    def _analyze_and_rank_chunks(
        self,
        raw_chunks: List[Dict],
        task_description: str,
        agent_role: str,
        task_type: str
    ) -> List[ContextChunk]:
        """Use RAG specialist to intelligently rank chunks"""
        
        analysis_prompt = f"""
        Task: {task_description}
        Agent Role: {agent_role}
        Task Type: {task_type}
        
        Rank these code chunks by relevance (1-5 scale):
        
        {self._format_chunks_for_analysis(raw_chunks[:10])}
        
        For each chunk, provide:
        - relevance_score (1-5)
        - context_type (code_implementation|api_reference|examples|documentation|tests)
        - key_dependencies (list of other files this depends on)
        
        Format as JSON list.
        """
        
        # This would use the RAG specialist to intelligently rank
        # For now, simplified scoring
        chunks = []
        for i, chunk in enumerate(raw_chunks):
            chunks.append(ContextChunk(
                content=chunk["text"],
                file_path=chunk["file_path"],
                context_type=ContextType.CODE_IMPLEMENTATION,
                relevance_score=5.0 - (i * 0.1),  # Simple decay
                token_count=len(chunk["text"]) // 4,  # Rough estimate
                dependencies=[]
            ))
        
        return sorted(chunks, key=lambda x: x.relevance_score, reverse=True)
    
    def _allocate_context_budget(
        self,
        chunks: List[ContextChunk],
        budget_tokens: int,
        agent_role: str
    ) -> List[ContextChunk]:
        """Smart allocation based on agent needs"""
        
        # Different agents need different context types
        if agent_role == "executor":
            # Executors need implementation details and examples
            priority_types = [
                ContextType.CODE_IMPLEMENTATION,
                ContextType.EXAMPLES,
                ContextType.API_REFERENCE
            ]
        elif agent_role == "planner":
            # Planners need high-level structure and API docs
            priority_types = [
                ContextType.API_REFERENCE,
                ContextType.DOCUMENTATION,
                ContextType.CODE_IMPLEMENTATION
            ]
        else:
            # Default priority
            priority_types = list(ContextType)
        
        # Allocate budget by priority
        selected = []
        used_tokens = 0
        
        # First pass: high-priority, high-relevance chunks
        for context_type in priority_types:
            type_chunks = [c for c in chunks if c.context_type == context_type]
            for chunk in type_chunks:
                if used_tokens + chunk.token_count <= budget_tokens:
                    selected.append(chunk)
                    used_tokens += chunk.token_count
                else:
                    break
            
            if used_tokens >= budget_tokens * 0.8:  # Use 80% of budget
                break
        
        return selected
    
    def _package_context(
        self, 
        chunks: List[ContextChunk], 
        task_description: str
    ) -> Dict[str, any]:
        """Package context into final format"""
        
        total_tokens = sum(c.token_count for c in chunks)
        key_files = list(set(c.file_path for c in chunks))
        
        # Generate summary
        summary = f"Context for: {task_description}\n"
        summary += f"Key files: {', '.join(key_files[:5])}\n"
        summary += f"Total context: {total_tokens:,} tokens"
        
        return {
            "chunks": chunks,
            "total_tokens": total_tokens,
            "context_summary": summary,
            "key_files": key_files,
            "missing_info": []  # TODO: Detect what's missing
        }
    
    def _format_chunks_for_analysis(self, chunks: List[Dict]) -> str:
        """Format chunks for LLM analysis"""
        formatted = []
        for i, chunk in enumerate(chunks):
            formatted.append(f"""
Chunk {i+1}:
File: {chunk['file_path']}
Content: {chunk['text'][:200]}...
""")
        return "\n".join(formatted)

class ContextStrategy:
    """
    Defines context strategies for different scenarios
    """
    
    @staticmethod
    def get_strategy(task_type: str, agent_role: str) -> Dict[str, any]:
        """Get context strategy for task/agent combination"""
        
        strategies = {
            ("coding", "executor"): {
                "budget_tokens": 80_000,
                "priority_types": ["code_implementation", "examples"],
                "include_tests": True,
                "include_dependencies": True
            },
            ("planning", "planner"): {
                "budget_tokens": 50_000,
                "priority_types": ["api_reference", "documentation"],
                "include_tests": False,
                "include_dependencies": False
            },
            ("debugging", "executor"): {
                "budget_tokens": 100_000,
                "priority_types": ["code_implementation", "tests"],
                "include_tests": True,
                "include_dependencies": True
            }
        }
        
        return strategies.get((task_type, agent_role), {
            "budget_tokens": 50_000,
            "priority_types": ["code_implementation"],
            "include_tests": True,
            "include_dependencies": False
        })