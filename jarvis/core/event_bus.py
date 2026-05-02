"""
J.A.R.V.I.S. - Event Bus Module
Async pub/sub system for agent communication
"""

import asyncio
from typing import Callable, Dict, List, Any, Optional, Set
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import json
import uuid


class EventType(Enum):
    """Types of events in the system"""
    COMMAND = "command"
    RESPONSE = "response"
    STATUS_UPDATE = "status_update"
    ERROR = "error"
    TASK_COMPLETE = "task_complete"
    MEMORY_READ = "memory_read"
    MEMORY_WRITE = "memory_write"
    SYSTEM_ALERT = "system_alert"
    USER_INPUT = "user_input"
    VOICE_COMMAND = "voice_command"
    SCHEDULED_TASK = "scheduled_task"


@dataclass
class Event:
    """Represents an event in the system"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    type: EventType = EventType.COMMAND
    source: str = ""
    target: Optional[str] = None
    payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 0  # Higher = more urgent
    correlation_id: Optional[str] = None  # Link related events
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "source": self.source,
            "target": self.target,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority,
            "correlation_id": self.correlation_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Event":
        return cls(
            id=data.get("id", str(uuid.uuid4())),
            type=EventType(data.get("type", "command")),
            source=data.get("source", ""),
            target=data.get("target"),
            payload=data.get("payload", {}),
            timestamp=datetime.fromisoformat(data["timestamp"]) if "timestamp" in data else datetime.now(),
            priority=data.get("priority", 0),
            correlation_id=data.get("correlation_id")
        )


class Subscription:
    """Represents a subscription to events"""
    
    def __init__(self, callback: Callable, event_types: Optional[Set[EventType]] = None, 
                 filter_func: Optional[Callable[[Event], bool]] = None):
        self.callback = callback
        self.event_types = event_types or set(EventType)
        self.filter_func = filter_func
        self.active = True
    
    def matches(self, event: Event) -> bool:
        """Check if an event matches this subscription"""
        if not self.active:
            return False
        if event.type not in self.event_types:
            return False
        if self.filter_func and not self.filter_func(event):
            return False
        return True


class EventBus:
    """
    Async event bus for agent communication.
    Implements pub/sub pattern with filtering and priorities.
    """
    
    def __init__(self):
        self._subscriptions: Dict[str, List[Subscription]] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._event_history: List[Event] = []
        self._max_history = 1000
        self._pending_events: Dict[str, Event] = {}  # correlation_id -> event
        self._response_handlers: Dict[str, asyncio.Future] = {}
    
    async def start(self):
        """Start the event bus processing loop"""
        self._running = True
        asyncio.create_task(self._process_events())
    
    async def stop(self):
        """Stop the event bus"""
        self._running = False
    
    def subscribe(self, subscriber_id: str, callback: Callable, 
                  event_types: Optional[List[EventType]] = None,
                  filter_func: Optional[Callable[[Event], bool]] = None) -> str:
        """
        Subscribe to events.
        
        Args:
            subscriber_id: Unique identifier for the subscriber
            callback: Async function to call when matching event arrives
            event_types: List of event types to subscribe to (None = all)
            filter_func: Optional function to filter events further
        
        Returns:
            Subscription ID
        """
        if subscriber_id not in self._subscriptions:
            self._subscriptions[subscriber_id] = []
        
        sub_types = set(event_types) if event_types else set(EventType)
        subscription = Subscription(callback, sub_types, filter_func)
        self._subscriptions[subscriber_id].append(subscription)
        
        return f"{subscriber_id}_{len(self._subscriptions[subscriber_id]) - 1}"
    
    def unsubscribe(self, subscriber_id: str, subscription_id: Optional[str] = None):
        """Unsubscribe from events"""
        if subscriber_id in self._subscriptions:
            if subscription_id:
                # Remove specific subscription
                idx = int(subscription_id.split("_")[-1])
                if idx < len(self._subscriptions[subscriber_id]):
                    self._subscriptions[subscriber_id][idx].active = False
            else:
                # Remove all subscriptions for this subscriber
                for sub in self._subscriptions[subscriber_id]:
                    sub.active = False
    
    async def publish(self, event: Event, wait_for_response: bool = False, 
                      timeout: float = 30.0) -> Optional[Event]:
        """
        Publish an event to the bus.
        
        Args:
            event: The event to publish
            wait_for_response: If True, wait for a response event
            timeout: Timeout for waiting
        
        Returns:
            Response event if wait_for_response is True, else None
        """
        # Add to queue
        await self._event_queue.put(event)
        
        # Track in history
        self._event_history.append(event)
        if len(self._event_history) > self._max_history:
            self._event_history.pop(0)
        
        # Wait for response if requested
        if wait_for_response:
            future = asyncio.Future()
            self._response_handlers[event.id] = future
            
            try:
                response = await asyncio.wait_for(future, timeout=timeout)
                return response
            except asyncio.TimeoutError:
                return None
            finally:
                del self._response_handlers[event.id]
        
        return None
    
    async def publish_and_wait(self, event: Event, response_type: EventType,
                               timeout: float = 30.0) -> Optional[Event]:
        """Publish an event and wait for a specific response type"""
        event.correlation_id = event.id
        self._pending_events[event.id] = event
        
        async def check_response(e: Event):
            if (e.correlation_id == event.id and 
                e.type == response_type and
                e.source != event.source):
                return True
            return False
        
        response_received = asyncio.Event()
        response_event = None
        
        def on_response(e: Event):
            nonlocal response_event, response_received
            response_event = e
            response_received.set()
        
        sub_id = self.subscribe("temp_response_handler", lambda e: None, 
                                [response_type], check_response)
        
        await self.publish(event)
        
        try:
            await asyncio.wait_for(response_received.wait(), timeout=timeout)
            return response_event
        except asyncio.TimeoutError:
            return None
        finally:
            self.unsubscribe("temp_response_handler", sub_id)
    
    async def _process_events(self):
        """Process events from the queue"""
        while self._running:
            try:
                event = await asyncio.wait_for(self._event_queue.get(), timeout=1.0)
                await self._dispatch_event(event)
                
                # Check if this is a response to a pending request
                if event.correlation_id and event.correlation_id in self._response_handlers:
                    future = self._response_handlers[event.correlation_id]
                    if not future.done():
                        future.set_result(event)
                        
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                print(f"Event bus error: {e}")
    
    async def _dispatch_event(self, event: Event):
        """Dispatch an event to all matching subscribers"""
        tasks = []
        
        for subscriber_id, subscriptions in self._subscriptions.items():
            for subscription in subscriptions:
                if subscription.matches(event):
                    try:
                        if asyncio.iscoroutinefunction(subscription.callback):
                            task = subscription.callback(event)
                        else:
                            task = asyncio.create_task(
                                asyncio.to_thread(subscription.callback, event)
                            )
                        tasks.append(task)
                    except Exception as e:
                        print(f"Error dispatching to {subscriber_id}: {e}")
        
        # Run all tasks concurrently
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
    
    def get_event_history(self, limit: int = 100, 
                          event_type: Optional[EventType] = None) -> List[Event]:
        """Get recent event history"""
        history = self._event_history
        
        if event_type:
            history = [e for e in history if e.type == event_type]
        
        return history[-limit:]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get event bus statistics"""
        active_subs = sum(
            len([s for s in subs if s.active])
            for subs in self._subscriptions.values()
        )
        
        return {
            "queue_size": self._event_queue.qsize(),
            "total_subscribers": len(self._subscriptions),
            "active_subscriptions": active_subs,
            "events_processed": len(self._event_history),
            "pending_responses": len(self._pending_events)
        }


class AgentRegistry:
    """Registry for tracking available agents"""
    
    def __init__(self, event_bus: EventBus):
        self.event_bus = event_bus
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._agent_capabilities: Dict[str, List[str]] = {}
    
    def register_agent(self, agent_id: str, name: str, capabilities: List[str],
                       metadata: Optional[Dict] = None):
        """Register an agent with the system"""
        self._agents[agent_id] = {
            "name": name,
            "capabilities": capabilities,
            "metadata": metadata or {},
            "registered_at": datetime.now(),
            "status": "active"
        }
        self._agent_capabilities[agent_id] = capabilities
        
        # Announce registration
        event = Event(
            type=EventType.STATUS_UPDATE,
            source="registry",
            payload={
                "action": "agent_registered",
                "agent_id": agent_id,
                "name": name,
                "capabilities": capabilities
            }
        )
        asyncio.create_task(self.event_bus.publish(event))
    
    def unregister_agent(self, agent_id: str):
        """Unregister an agent"""
        if agent_id in self._agents:
            self._agents[agent_id]["status"] = "inactive"
            
            event = Event(
                type=EventType.STATUS_UPDATE,
                source="registry",
                payload={"action": "agent_unregistered", "agent_id": agent_id}
            )
            asyncio.create_task(self.event_bus.publish(event))
    
    def find_agents_by_capability(self, capability: str) -> List[str]:
        """Find agents that have a specific capability"""
        matching = []
        for agent_id, caps in self._agent_capabilities.items():
            if capability.lower() in [c.lower() for c in caps]:
                if self._agents[agent_id]["status"] == "active":
                    matching.append(agent_id)
        return matching
    
    def get_agent_info(self, agent_id: str) -> Optional[Dict]:
        """Get information about an agent"""
        return self._agents.get(agent_id)
    
    def list_agents(self) -> List[Dict]:
        """List all registered agents"""
        return [
            {"id": aid, **info}
            for aid, info in self._agents.items()
        ]


# Global event bus instance
_global_event_bus: Optional[EventBus] = None
_global_registry: Optional[AgentRegistry] = None


def get_event_bus() -> EventBus:
    """Get or create the global event bus"""
    global _global_event_bus
    if _global_event_bus is None:
        _global_event_bus = EventBus()
    return _global_event_bus


def get_agent_registry() -> AgentRegistry:
    """Get or create the global agent registry"""
    global _global_registry
    if _global_registry is None:
        _global_registry = AgentRegistry(get_event_bus())
    return _global_registry


if __name__ == "__main__":
    # Test the event bus
    async def test_event_bus():
        bus = EventBus()
        await bus.start()
        
        received_events = []
        
        async def on_event(event: Event):
            received_events.append(event)
            print(f"Received: {event.type.value} from {event.source}")
        
        # Subscribe to events
        bus.subscribe("test_subscriber", on_event, [EventType.COMMAND, EventType.STATUS_UPDATE])
        
        # Publish some events
        for i in range(5):
            event = Event(
                type=EventType.COMMAND,
                source="test",
                payload={"index": i}
            )
            await bus.publish(event)
            await asyncio.sleep(0.1)
        
        # Get stats
        print("\nEvent Bus Stats:")
        print(bus.get_stats())
        
        # Get history
        print("\nEvent History:")
        for event in bus.get_event_history(limit=5):
            print(f"  - {event.type.value}: {event.payload}")
        
        await bus.stop()
    
    asyncio.run(test_event_bus())
