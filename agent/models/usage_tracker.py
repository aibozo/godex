# Usage tracking with persistence
import json
import sqlite3
from pathlib import Path
from datetime import datetime, date
from typing import List, Dict, Optional, Tuple
from pydantic import BaseModel, Field
from contextlib import contextmanager

from agent.config import get_settings
from .registry import get_model_info, calculate_cost

class UsageRecord(BaseModel):
    """Record of a single LLM API call"""
    timestamp: datetime
    model_id: str
    provider: str
    input_tokens: int
    output_tokens: int
    cost: float
    thinking_mode: bool = False
    task_id: Optional[str] = None
    component: Optional[str] = None  # planner, executor, reflexion, etc.
    
class DailyUsage(BaseModel):
    """Aggregated daily usage statistics"""
    date: date
    total_cost: float
    total_input_tokens: int
    total_output_tokens: int
    model_breakdown: Dict[str, Dict[str, float]]  # model_id -> {cost, input_tokens, output_tokens}
    component_breakdown: Dict[str, float]  # component -> cost

class UsageTracker:
    """Tracks and persists LLM usage across all providers"""
    
    def __init__(self, db_path: Optional[Path] = None):
        self.settings = get_settings()
        if db_path is None:
            db_path = Path(self.settings.agent_home) / "memory" / "usage.db"
        
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema"""
        with self._get_db() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS usage_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model_id TEXT NOT NULL,
                    provider TEXT NOT NULL,
                    input_tokens INTEGER NOT NULL,
                    output_tokens INTEGER NOT NULL,
                    cost REAL NOT NULL,
                    thinking_mode BOOLEAN DEFAULT FALSE,
                    task_id TEXT,
                    component TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # Create indexes for common queries
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_timestamp 
                ON usage_records(timestamp)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_model_id 
                ON usage_records(model_id)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_task_id 
                ON usage_records(task_id)
            """)
            
            # Daily summary table for faster aggregations
            conn.execute("""
                CREATE TABLE IF NOT EXISTS daily_summaries (
                    date TEXT PRIMARY KEY,
                    total_cost REAL NOT NULL,
                    total_input_tokens INTEGER NOT NULL,
                    total_output_tokens INTEGER NOT NULL,
                    model_breakdown TEXT NOT NULL,  -- JSON
                    component_breakdown TEXT NOT NULL,  -- JSON
                    updated_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.commit()
    
    @contextmanager
    def _get_db(self):
        """Get a database connection"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def track_usage(
        self,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        thinking_mode: bool = False,
        task_id: Optional[str] = None,
        component: Optional[str] = None
    ) -> UsageRecord:
        """Track a single LLM API call"""
        # Get model info and calculate cost
        model_info = get_model_info(model_id)
        if not model_info:
            raise ValueError(f"Unknown model: {model_id}")
        
        cost = calculate_cost(model_id, input_tokens, output_tokens, thinking_mode)
        
        # Create record
        record = UsageRecord(
            timestamp=datetime.now(),
            model_id=model_id,
            provider=model_info.provider,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost=cost,
            thinking_mode=thinking_mode,
            task_id=task_id,
            component=component
        )
        
        # Check daily cost cap
        today_cost = self.get_today_cost()
        if today_cost + cost > self.settings.cost_cap_daily:
            raise ValueError(
                f"Daily cost cap of ${self.settings.cost_cap_daily} would be exceeded. "
                f"Current: ${today_cost:.2f}, New cost: ${cost:.2f}"
            )
        
        # Persist to database
        with self._get_db() as conn:
            conn.execute("""
                INSERT INTO usage_records 
                (timestamp, model_id, provider, input_tokens, output_tokens, 
                 cost, thinking_mode, task_id, component)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.timestamp.isoformat(),
                record.model_id,
                record.provider,
                record.input_tokens,
                record.output_tokens,
                record.cost,
                record.thinking_mode,
                record.task_id,
                record.component
            ))
            conn.commit()
        
        # Update daily summary
        self._update_daily_summary(record.timestamp.date())
        
        return record
    
    def get_today_cost(self) -> float:
        """Get total cost for today"""
        today = date.today()
        with self._get_db() as conn:
            result = conn.execute("""
                SELECT SUM(cost) as total_cost
                FROM usage_records
                WHERE DATE(timestamp) = ?
            """, (today.isoformat(),)).fetchone()
            
            return result["total_cost"] or 0.0
    
    def get_usage_by_date(self, target_date: date) -> DailyUsage:
        """Get usage statistics for a specific date"""
        with self._get_db() as conn:
            # Try to get from daily summary first
            summary = conn.execute("""
                SELECT * FROM daily_summaries WHERE date = ?
            """, (target_date.isoformat(),)).fetchone()
            
            if summary:
                return DailyUsage(
                    date=target_date,
                    total_cost=summary["total_cost"],
                    total_input_tokens=summary["total_input_tokens"],
                    total_output_tokens=summary["total_output_tokens"],
                    model_breakdown=json.loads(summary["model_breakdown"]),
                    component_breakdown=json.loads(summary["component_breakdown"])
                )
            
            # Calculate from raw records if no summary
            return self._calculate_daily_usage(target_date)
    
    def get_usage_by_task(self, task_id: str) -> Tuple[float, int, int]:
        """Get total cost and tokens for a specific task"""
        with self._get_db() as conn:
            result = conn.execute("""
                SELECT 
                    SUM(cost) as total_cost,
                    SUM(input_tokens) as total_input,
                    SUM(output_tokens) as total_output
                FROM usage_records
                WHERE task_id = ?
            """, (task_id,)).fetchone()
            
            return (
                result["total_cost"] or 0.0,
                result["total_input"] or 0,
                result["total_output"] or 0
            )
    
    def get_usage_by_model(self, model_id: str, days: int = 7) -> Dict[str, float]:
        """Get usage statistics for a specific model over the last N days"""
        with self._get_db() as conn:
            results = conn.execute("""
                SELECT 
                    DATE(timestamp) as date,
                    SUM(cost) as daily_cost,
                    SUM(input_tokens) as input_tokens,
                    SUM(output_tokens) as output_tokens
                FROM usage_records
                WHERE model_id = ?
                AND DATE(timestamp) >= DATE('now', '-' || ? || ' days')
                GROUP BY DATE(timestamp)
                ORDER BY date DESC
            """, (model_id, days)).fetchall()
            
            return {
                row["date"]: {
                    "cost": row["daily_cost"],
                    "input_tokens": row["input_tokens"],
                    "output_tokens": row["output_tokens"]
                }
                for row in results
            }
    
    def _calculate_daily_usage(self, target_date: date) -> DailyUsage:
        """Calculate daily usage from raw records"""
        with self._get_db() as conn:
            # Get all records for the date
            records = conn.execute("""
                SELECT * FROM usage_records
                WHERE DATE(timestamp) = ?
            """, (target_date.isoformat(),)).fetchall()
            
            total_cost = 0.0
            total_input = 0
            total_output = 0
            model_breakdown = {}
            component_breakdown = {}
            
            for record in records:
                total_cost += record["cost"]
                total_input += record["input_tokens"]
                total_output += record["output_tokens"]
                
                # Model breakdown
                model_id = record["model_id"]
                if model_id not in model_breakdown:
                    model_breakdown[model_id] = {
                        "cost": 0.0,
                        "input_tokens": 0,
                        "output_tokens": 0
                    }
                model_breakdown[model_id]["cost"] += record["cost"]
                model_breakdown[model_id]["input_tokens"] += record["input_tokens"]
                model_breakdown[model_id]["output_tokens"] += record["output_tokens"]
                
                # Component breakdown
                component = record["component"] or "unknown"
                if component not in component_breakdown:
                    component_breakdown[component] = 0.0
                component_breakdown[component] += record["cost"]
            
            return DailyUsage(
                date=target_date,
                total_cost=total_cost,
                total_input_tokens=total_input,
                total_output_tokens=total_output,
                model_breakdown=model_breakdown,
                component_breakdown=component_breakdown
            )
    
    def _update_daily_summary(self, target_date: date):
        """Update the daily summary for a specific date"""
        usage = self._calculate_daily_usage(target_date)
        
        with self._get_db() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO daily_summaries
                (date, total_cost, total_input_tokens, total_output_tokens,
                 model_breakdown, component_breakdown)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                usage.date.isoformat(),
                usage.total_cost,
                usage.total_input_tokens,
                usage.total_output_tokens,
                json.dumps(usage.model_breakdown),
                json.dumps(usage.component_breakdown)
            ))
            conn.commit()
    
    def get_usage_report(self, days: int = 7) -> str:
        """Generate a human-readable usage report"""
        report_lines = ["=== LLM Usage Report ===\n"]
        
        total_cost = 0.0
        total_input = 0
        total_output = 0
        
        for i in range(days):
            target_date = date.today() - timedelta(days=i)
            usage = self.get_usage_by_date(target_date)
            
            if usage.total_cost > 0:
                report_lines.append(f"\n{target_date.isoformat()}:")
                report_lines.append(f"  Total Cost: ${usage.total_cost:.2f}")
                report_lines.append(f"  Tokens: {usage.total_input_tokens:,} in / {usage.total_output_tokens:,} out")
                
                if usage.model_breakdown:
                    report_lines.append("  By Model:")
                    for model_id, stats in sorted(usage.model_breakdown.items(), 
                                                 key=lambda x: x[1]["cost"], 
                                                 reverse=True):
                        report_lines.append(f"    {model_id}: ${stats['cost']:.2f}")
                
                total_cost += usage.total_cost
                total_input += usage.total_input_tokens
                total_output += usage.total_output_tokens
        
        report_lines.append(f"\n{days}-Day Total: ${total_cost:.2f}")
        report_lines.append(f"Daily Average: ${total_cost/days:.2f}")
        report_lines.append(f"Total Tokens: {total_input:,} in / {total_output:,} out")
        
        return "\n".join(report_lines)


# Import timedelta for the report
from datetime import timedelta