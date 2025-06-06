"""
Message flow monitoring for debugging broker communication.
Tracks message lifecycle: sent -> received -> processed -> responded
"""

import time
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
from pathlib import Path


class MessageStatus(Enum):
    """Status of a message in the system."""
    CREATED = "created"
    SENT = "sent"
    RECEIVED = "received"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    NO_HANDLER = "no_handler"


@dataclass
class MessageEvent:
    """Event in a message's lifecycle."""
    timestamp: datetime
    status: MessageStatus
    details: str
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class MessageTrace:
    """Complete trace of a message through the system."""
    message_id: str
    sender: str
    recipient: str
    message_type: str
    created_at: datetime
    events: List[MessageEvent] = field(default_factory=list)
    
    def add_event(self, status: MessageStatus, details: str, error: Optional[str] = None, **metadata):
        """Add an event to the message trace."""
        event = MessageEvent(
            timestamp=datetime.now(),
            status=status,
            details=details,
            error=error,
            metadata=metadata
        )
        self.events.append(event)
    
    def get_duration(self) -> float:
        """Get total duration from creation to last event."""
        if not self.events:
            return 0.0
        return (self.events[-1].timestamp - self.created_at).total_seconds()
    
    def get_status(self) -> MessageStatus:
        """Get current status of the message."""
        if not self.events:
            return MessageStatus.CREATED
        return self.events[-1].status
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert trace to dictionary for serialization."""
        return {
            "message_id": self.message_id,
            "sender": self.sender,
            "recipient": self.recipient,
            "message_type": self.message_type,
            "created_at": self.created_at.isoformat(),
            "duration": self.get_duration(),
            "status": self.get_status().value,
            "events": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "status": e.status.value,
                    "details": e.details,
                    "error": e.error,
                    "metadata": e.metadata
                }
                for e in self.events
            ]
        }


class MessageMonitor:
    """Monitor for tracking message flow through the broker system."""
    
    def __init__(self, log_dir: str = "broker_logs"):
        self.traces: Dict[str, MessageTrace] = {}
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(exist_ok=True)
        self.enable_console_output = True
        
    def start_trace(self, message_id: str, sender: str, recipient: str, message_type: str) -> MessageTrace:
        """Start tracking a new message."""
        trace = MessageTrace(
            message_id=message_id,
            sender=sender,
            recipient=recipient,
            message_type=message_type,
            created_at=datetime.now()
        )
        self.traces[message_id] = trace
        
        if self.enable_console_output:
            print(f"[Monitor] Message {message_id[:8]}... created: {sender} -> {recipient}")
        
        return trace
    
    def record_event(self, message_id: str, status: MessageStatus, details: str, 
                    error: Optional[str] = None, **metadata):
        """Record an event for a message."""
        if message_id not in self.traces:
            # Create a minimal trace if we don't have one
            trace = MessageTrace(
                message_id=message_id,
                sender="unknown",
                recipient="unknown", 
                message_type="unknown",
                created_at=datetime.now()
            )
            self.traces[message_id] = trace
        
        trace = self.traces[message_id]
        trace.add_event(status, details, error, **metadata)
        
        if self.enable_console_output:
            status_color = {
                MessageStatus.SENT: "\033[94m",      # Blue
                MessageStatus.RECEIVED: "\033[92m",   # Green
                MessageStatus.COMPLETED: "\033[92m",  # Green
                MessageStatus.FAILED: "\033[91m",     # Red
                MessageStatus.TIMEOUT: "\033[93m",    # Yellow
                MessageStatus.NO_HANDLER: "\033[91m", # Red
            }.get(status, "")
            reset = "\033[0m" if status_color else ""
            
            msg = f"[Monitor] {message_id[:8]}... {status_color}{status.value}{reset}: {details}"
            if error:
                msg += f" (Error: {error})"
            print(msg)
    
    def get_trace(self, message_id: str) -> Optional[MessageTrace]:
        """Get trace for a specific message."""
        return self.traces.get(message_id)
    
    def get_recent_failures(self, limit: int = 10) -> List[MessageTrace]:
        """Get recent failed messages."""
        failed = [
            trace for trace in self.traces.values()
            if trace.get_status() in [MessageStatus.FAILED, MessageStatus.TIMEOUT, MessageStatus.NO_HANDLER]
        ]
        # Sort by most recent first
        failed.sort(key=lambda t: t.created_at, reverse=True)
        return failed[:limit]
    
    def save_trace(self, message_id: str):
        """Save a trace to disk for later analysis."""
        if message_id not in self.traces:
            return
        
        trace = self.traces[message_id]
        filename = f"{trace.created_at.strftime('%Y%m%d_%H%M%S')}_{message_id[:8]}.json"
        filepath = self.log_dir / filename
        
        with open(filepath, 'w') as f:
            json.dump(trace.to_dict(), f, indent=2)
    
    def print_summary(self):
        """Print summary of all tracked messages."""
        if not self.traces:
            print("\n[Monitor] No messages tracked")
            return
        
        print(f"\n[Monitor] Message Summary ({len(self.traces)} messages)")
        print("-" * 80)
        
        # Group by status
        by_status = {}
        for trace in self.traces.values():
            status = trace.get_status()
            if status not in by_status:
                by_status[status] = []
            by_status[status].append(trace)
        
        # Print status counts
        for status in MessageStatus:
            count = len(by_status.get(status, []))
            if count > 0:
                print(f"  {status.value}: {count}")
        
        # Print recent failures
        failures = self.get_recent_failures(5)
        if failures:
            print("\nRecent Failures:")
            for trace in failures:
                last_event = trace.events[-1] if trace.events else None
                print(f"  - {trace.message_id[:8]}... ({trace.sender} -> {trace.recipient})")
                if last_event:
                    print(f"    {last_event.details}")
                    if last_event.error:
                        print(f"    Error: {last_event.error}")
    
    def clear(self):
        """Clear all traces."""
        self.traces.clear()


# Global monitor instance
_monitor = None

def get_message_monitor() -> MessageMonitor:
    """Get the global message monitor instance."""
    global _monitor
    if _monitor is None:
        _monitor = MessageMonitor()
    return _monitor