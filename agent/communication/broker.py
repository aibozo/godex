"""
Message broker for routing inter-agent communications.
"""

from typing import Dict, Any, List, Optional, Callable
import threading
import time
import queue
from collections import defaultdict
import datetime

from .protocol import AgentMessage, MessageType
from .monitor import get_message_monitor, MessageStatus


class MessageBroker:
    """
    Central message broker for routing messages between agents.
    
    Handles:
    - Message routing to appropriate agents
    - Response correlation  
    - Message queuing and delivery
    - Broadcast messaging
    - Error handling and timeouts
    """
    
    _instance: Optional["MessageBroker"] = None
    _lock = threading.Lock()
    
    def __new__(cls) -> "MessageBroker":
        """Singleton pattern for message broker."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if getattr(self, '_initialized', False):
            return
            
        # Agent registry: maps agent names to handler functions
        self._agent_handlers: Dict[str, Callable[[AgentMessage], Dict[str, Any]]] = {}
        
        # Message queues for each agent
        self._message_queues: Dict[str, queue.Queue] = defaultdict(lambda: queue.Queue())
        
        # Pending responses tracking
        self._pending_responses: Dict[str, AgentMessage] = {}
        self._response_events: Dict[str, threading.Event] = {}
        
        # Message history for debugging
        self._message_history: List[AgentMessage] = []
        self._max_history_size = 1000
        
        # Worker threads for async processing
        self._worker_threads: Dict[str, threading.Thread] = {}
        self._shutdown_event = threading.Event()
        
        # Statistics
        self._stats = {
            "messages_sent": 0,
            "messages_delivered": 0,
            "messages_failed": 0,
            "responses_matched": 0
        }
        
        self._initialized = True
    
    def register_agent(self, agent_name: str, handler: Callable[[AgentMessage], Dict[str, Any]]) -> None:
        """
        Register an agent with the broker.
        
        Args:
            agent_name: Name of the agent (e.g., "manager", "planner")
            handler: Function to handle incoming messages for this agent
        """
        self._agent_handlers[agent_name] = handler
        
        # Start worker thread for this agent if not already running
        if agent_name not in self._worker_threads:
            thread = threading.Thread(
                target=self._agent_worker,
                args=(agent_name,),
                daemon=True,
                name=f"broker-worker-{agent_name}"
            )
            thread.start()
            self._worker_threads[agent_name] = thread
    
    def get_stats(self) -> Dict[str, Any]:
        """Get broker statistics."""
        return {
            **self._stats,
            "registered_agents": list(self._agent_handlers.keys()),
            "pending_responses": len(self._pending_responses),
            "message_history_size": len(self._message_history)
        }
    
    def _agent_worker(self, agent_name: str) -> None:
        """Worker thread for processing messages for a specific agent."""
        while not self._shutdown_event.is_set():
            try:
                # Get message from queue with timeout
                message = self._message_queues[agent_name].get(timeout=0.1)
                
                # Monitor that message was received
                monitor = get_message_monitor()
                monitor.record_event(
                    message.message_id,
                    MessageStatus.RECEIVED,
                    f"Message received by {agent_name}"
                )
                
                # Process message
                if agent_name in self._agent_handlers:
                    handler = self._agent_handlers[agent_name]
                    try:
                        monitor.record_event(
                            message.message_id,
                            MessageStatus.PROCESSING,
                            f"{agent_name} processing message"
                        )
                        
                        response_payload = handler(message)
                        
                        # If this was a request, create and store the response message
                        if message.message_type == MessageType.REQUEST:
                            # Create a proper response message
                            response_message = message.create_response(
                                payload=response_payload,
                                message_type=MessageType.RESPONSE
                            )
                            self._pending_responses[message.message_id] = response_message
                            
                            # Signal that response is ready
                            if message.message_id in self._response_events:
                                self._response_events[message.message_id].set()
                            
                            monitor.record_event(
                                message.message_id,
                                MessageStatus.COMPLETED,
                                f"{agent_name} completed processing",
                                response_size=len(str(response_payload))
                            )
                                
                    except Exception as e:
                        print(f"[Broker] Error handling message for {agent_name}: {e}")
                        import traceback
                        traceback.print_exc()
                        monitor.record_event(
                            message.message_id,
                            MessageStatus.FAILED,
                            f"{agent_name} failed to process message",
                            error=str(e)
                        )
                        
                self._stats["messages_delivered"] += 1
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"[Broker] Worker error for {agent_name}: {e}")
                self._stats["messages_failed"] += 1
    
    def route_message(self, message: AgentMessage) -> None:
        """
        Route a message to the appropriate agent.
        
        Args:
            message: Message to route
        """
        # Start monitoring
        monitor = get_message_monitor()
        monitor.start_trace(
            message.message_id,
            message.sender,
            message.recipient,
            message.message_type.value
        )
        
        # Add to history
        self._message_history.append(message)
        if len(self._message_history) > self._max_history_size:
            self._message_history.pop(0)
        
        # Route to recipient
        if message.recipient in self._agent_handlers:
            self._message_queues[message.recipient].put(message)
            self._stats["messages_sent"] += 1
            monitor.record_event(
                message.message_id,
                MessageStatus.SENT,
                f"Message queued for {message.recipient}"
            )
        else:
            print(f"[Broker] No handler for recipient: {message.recipient}")
            self._stats["messages_failed"] += 1
            monitor.record_event(
                message.message_id,
                MessageStatus.NO_HANDLER,
                f"No handler registered for {message.recipient}",
                error="Agent not registered"
            )
    
    def send_request(self, message: AgentMessage, timeout: float = 30.0) -> Optional[Dict[str, Any]]:
        """
        Send a request message and wait for response.
        
        Args:
            message: Request message to send
            timeout: Maximum time to wait for response
            
        Returns:
            Response from agent or None if timeout
        """
        # Create event for this request
        self._response_events[message.message_id] = threading.Event()
        
        # Route the message
        self.route_message(message)
        
        # Wait for response
        if self._response_events[message.message_id].wait(timeout):
            # Get response
            response = self._pending_responses.pop(message.message_id, None)
            del self._response_events[message.message_id]
            self._stats["responses_matched"] += 1
            return response
        else:
            # Timeout
            del self._response_events[message.message_id]
            print(f"[Broker] Request timeout for message {message.message_id}")
            monitor = get_message_monitor()
            monitor.record_event(
                message.message_id,
                MessageStatus.TIMEOUT,
                f"Request timed out after {timeout}s",
                error="No response received"
            )
            return None
    
    def shutdown(self) -> None:
        """Shutdown the message broker."""
        self._shutdown_event.set()
        # Clear all registrations
        self._agent_handlers.clear()
        self._message_queues.clear()
        self._pending_responses.clear()