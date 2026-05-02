"""
J.A.R.V.I.S. - Commander Agent
Master router that coordinates all other agents
"""

import asyncio
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime
import sys
import os

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus, Event, EventType, get_event_bus, get_agent_registry
from core.nlp_engine import IntentClassifier, CommandParser, Intent, IntentResult


@dataclass
class Task:
    """Represents a task to be executed"""
    id: str
    description: str
    intent: IntentResult
    assigned_agent: Optional[str] = None
    status: str = "pending"  # pending, running, completed, failed
    result: Optional[Any] = None
    created_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "description": self.description,
            "intent": self.intent.to_dict() if self.intent else None,
            "assigned_agent": self.assigned_agent,
            "status": self.status,
            "result": self.result,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "error": self.error
        }


class CommanderAgent:
    """
    The Commander Agent is the central coordinator for J.A.R.V.I.S.
    It receives user input, classifies intent, and routes tasks to appropriate agents.
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or get_event_bus()
        self.registry = get_agent_registry()
        self.intent_classifier = IntentClassifier()
        self.command_parser = CommandParser()
        
        self.agent_id = "commander"
        self.capabilities = [
            "task_routing",
            "intent_classification", 
            "multi_agent_coordination",
            "conversation_management",
            "fallback_handling"
        ]
        
        self._tasks: Dict[str, Task] = {}
        self._active_conversations: Dict[str, List[Dict]] = {}
        self._running = False
        
        # Register with the system
        self._register_self()
    
    def _register_self(self):
        """Register commander agent with the registry"""
        self.registry.register_agent(
            agent_id=self.agent_id,
            name="Commander",
            capabilities=self.capabilities,
            metadata={
                "description": "Central coordinator for all J.A.R.V.I.S. agents",
                "priority": 1
            }
        )
    
    async def start(self):
        """Start the commander agent"""
        self._running = True
        
        # Subscribe to user input events
        self.event_bus.subscribe(
            subscriber_id=self.agent_id,
            callback=self._on_user_input,
            event_types=[EventType.USER_INPUT, EventType.VOICE_COMMAND]
        )
        
        # Subscribe to task completion events
        self.event_bus.subscribe(
            subscriber_id=self.agent_id,
            callback=self._on_task_complete,
            event_types=[EventType.TASK_COMPLETE, EventType.ERROR]
        )
        
        print(f"[{self.agent_id.upper()}] Commander agent started")
    
    async def stop(self):
        """Stop the commander agent"""
        self._running = False
        self.event_bus.unsubscribe(self.agent_id)
        print(f"[{self.agent_id.upper()}] Commander agent stopped")
    
    async def _on_user_input(self, event: Event):
        """Handle incoming user input"""
        text = event.payload.get("text", "")
        conversation_id = event.payload.get("conversation_id", "default")
        
        if not text:
            return
        
        # Classify the intent
        intent_result = self.intent_classifier.classify(text)
        
        # Create a task
        task = Task(
            id=f"task_{datetime.now().strftime('%Y%m%d%H%M%S')}_{len(self._tasks)}",
            description=text,
            intent=intent_result
        )
        
        self._tasks[task.id] = task
        
        # Store conversation context
        if conversation_id not in self._active_conversations:
            self._active_conversations[conversation_id] = []
        self._active_conversations[conversation_id].append({
            "role": "user",
            "content": text,
            "timestamp": datetime.now()
        })
        
        # Route to appropriate agent
        await self._route_task(task, conversation_id)
    
    async def _route_task(self, task: Task, conversation_id: str = "default"):
        """Route a task to the appropriate agent(s)"""
        suggested_agents = self.intent_classifier.get_suggested_agents(task.intent)
        
        # Find available agents
        available_agents = []
        for agent_name in suggested_agents:
            agent_info = self.registry.get_agent_info(agent_name)
            if agent_info and agent_info.get("status") == "active":
                available_agents.append(agent_name)
        
        if not available_agents:
            available_agents = ["commander"]  # Fallback to commander
        
        # Assign to first available agent
        task.assigned_agent = available_agents[0]
        task.status = "running"
        
        print(f"[{self.agent_id.upper()}] Routing task '{task.id}' to '{task.assigned_agent}'")
        
        # Create command event for the target agent
        command_event = Event(
            type=EventType.COMMAND,
            source=self.agent_id,
            target=task.assigned_agent,
            payload={
                "task_id": task.id,
                "action": task.intent.intent.value,
                "input": task.description,
                "intent": task.intent.to_dict(),
                "conversation_id": conversation_id,
                "parameters": self.command_parser.parse_command(task.description)
            },
            correlation_id=task.id
        )
        
        # Publish the command
        await self.event_bus.publish(command_event)
    
    async def _on_task_complete(self, event: Event):
        """Handle task completion from agents"""
        task_id = event.payload.get("task_id")
        
        if task_id and task_id in self._tasks:
            task = self._tasks[task_id]
            
            if event.type == EventType.TASK_COMPLETE:
                task.status = "completed"
                task.result = event.payload.get("result")
                task.completed_at = datetime.now()
                
                print(f"[{self.agent_id.upper()}] Task '{task_id}' completed successfully")
                
            elif event.type == EventType.ERROR:
                task.status = "failed"
                task.error = event.payload.get("error")
                task.completed_at = datetime.now()
                
                print(f"[{self.agent_id.upper()}] Task '{task_id}' failed: {task.error}")
                
                # Try fallback - route to another agent or handle directly
                await self._handle_failed_task(task)
            
            # Send response back to user
            await self._send_response(task, event.payload.get("conversation_id", "default"))
    
    async def _handle_failed_task(self, task: Task):
        """Handle a failed task - try alternative approaches"""
        # Get alternative agents
        suggested_agents = self.intent_classifier.get_suggested_agents(task.intent)
        
        # Try next available agent
        for agent_name in suggested_agents:
            if agent_name != task.assigned_agent:
                agent_info = self.registry.get_agent_info(agent_name)
                if agent_info and agent_info.get("status") == "active":
                    print(f"[{self.agent_id.upper()}] Retrying task '{task.id}' with '{agent_name}'")
                    task.assigned_agent = agent_name
                    task.status = "running"
                    task.error = None
                    
                    # Re-route the task
                    await self._route_task(task)
                    return
        
        # If no alternative agents, respond with error message
        print(f"[{self.agent_id.upper()}] No alternative agents for task '{task.id}'")
    
    async def _send_response(self, task: Task, conversation_id: str):
        """Send response back to user"""
        response_text = self._generate_response(task)
        
        # Store in conversation history
        if conversation_id in self._active_conversations:
            self._active_conversations[conversation_id].append({
                "role": "assistant",
                "content": response_text,
                "timestamp": datetime.now()
            })
        
        # Publish response event
        response_event = Event(
            type=EventType.RESPONSE,
            source=self.agent_id,
            payload={
                "task_id": task.id,
                "text": response_text,
                "conversation_id": conversation_id,
                "task_status": task.status
            }
        )
        
        await self.event_bus.publish(response_event)
    
    def _generate_response(self, task: Task) -> str:
        """Generate a human-readable response based on task result"""
        if task.status == "completed":
            result = task.result
            
            if isinstance(result, dict):
                # Format structured results
                if "message" in result:
                    return result["message"]
                elif "output" in result:
                    return str(result["output"])
                else:
                    return f"Task completed: {result}"
            elif isinstance(result, str):
                return result
            else:
                return f"Task '{task.description}' completed successfully."
        
        elif task.status == "failed":
            error_msg = task.error or "Unknown error occurred"
            return f"I apologize, sir, but I encountered an issue: {error_msg}. Shall I try an alternative approach?"
        
        else:
            return f"Processing your request: {task.description}"
    
    def process_direct(self, text: str) -> Dict[str, Any]:
        """Process a command directly (synchronous, for testing)"""
        intent_result = self.intent_classifier.classify(text)
        
        return {
            "input": text,
            "intent": intent_result.intent.value,
            "confidence": intent_result.confidence,
            "entities": intent_result.entities,
            "suggested_agents": self.intent_classifier.get_suggested_agents(intent_result),
            "parsed_command": self.command_parser.parse_command(text)
        }
    
    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """Get status of a specific task"""
        if task_id in self._tasks:
            return self._tasks[task_id].to_dict()
        return None
    
    def list_tasks(self, limit: int = 10) -> List[Dict]:
        """List recent tasks"""
        sorted_tasks = sorted(
            self._tasks.values(),
            key=lambda t: t.created_at,
            reverse=True
        )
        return [t.to_dict() for t in sorted_tasks[:limit]]
    
    def get_conversation_history(self, conversation_id: str = "default") -> List[Dict]:
        """Get conversation history"""
        return self._active_conversations.get(conversation_id, [])
    
    def clear_conversation(self, conversation_id: str = "default"):
        """Clear conversation history"""
        if conversation_id in self._active_conversations:
            del self._active_conversations[conversation_id]
    
    def get_status(self) -> Dict[str, Any]:
        """Get commander agent status"""
        return {
            "agent_id": self.agent_id,
            "running": self._running,
            "capabilities": self.capabilities,
            "active_tasks": len([t for t in self._tasks.values() if t.status == "running"]),
            "total_tasks": len(self._tasks),
            "active_conversations": len(self._active_conversations),
            "registered_agents": len(self.registry.list_agents())
        }


# Singleton instance
_commander_instance: Optional[CommanderAgent] = None


def get_commander(event_bus: Optional[EventBus] = None) -> CommanderAgent:
    """Get or create the commander agent singleton"""
    global _commander_instance
    if _commander_instance is None:
        _commander_instance = CommanderAgent(event_bus)
    return _commander_instance


if __name__ == "__main__":
    # Test the commander agent
    async def test_commander():
        bus = EventBus()
        await bus.start()
        
        commander = CommanderAgent(bus)
        await commander.start()
        
        # Test direct processing
        test_commands = [
            "Hello JARVIS",
            "Open Chrome",
            "What's my CPU usage?",
            "Write a Python function to sort a list",
            "Play some music",
        ]
        
        print("=" * 60)
        print("J.A.R.V.I.S. Commander Agent Test")
        print("=" * 60)
        
        for cmd in test_commands:
            print(f"\nCommand: {cmd}")
            result = commander.process_direct(cmd)
            print(f"  Intent: {result['intent']} ({result['confidence']:.2f})")
            print(f"  Suggested Agents: {result['suggested_agents']}")
            print(f"  Parsed Action: {result['parsed_command']['action']}")
            print(f"  Target: {result['parsed_command']['target']}")
        
        # Get status
        print("\n" + "=" * 60)
        print("Commander Status:")
        print(commander.get_status())
        
        await commander.stop()
        await bus.stop()
    
    asyncio.run(test_commander())
