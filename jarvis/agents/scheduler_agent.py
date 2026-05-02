"""
J.A.R.V.I.S. - Scheduler Agent
Cron jobs, reminders, and automation triggers
"""

import os
import sys
import asyncio
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus, Event, EventType, get_event_bus, get_agent_registry


@dataclass
class ScheduledTask:
    id: str
    name: str
    action: str
    schedule: str  # cron-like or "once"
    next_run: Optional[datetime] = None
    enabled: bool = True
    last_run: Optional[datetime] = None
    metadata: Dict = field(default_factory=dict)


class SchedulerAgent:
    """Scheduler Agent - Handles reminders and automated tasks"""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or get_event_bus()
        
        self.agent_id = "scheduler"
        self.capabilities = [
            "scheduled_tasks",
            "reminders",
            "cron_jobs",
            "automation_triggers"
        ]
        
        self._tasks: Dict[str, ScheduledTask] = {}
        self._running = False
        self._scheduler_task = None
        
        self._register_self()
    
    def _register_self(self):
        self.registry = get_agent_registry()
        self.registry.register_agent(
            agent_id=self.agent_id,
            name="Scheduler",
            capabilities=self.capabilities,
            metadata={"description": "Scheduled tasks and reminders"}
        )
    
    async def start(self):
        self._running = True
        self.event_bus.subscribe(
            subscriber_id=self.agent_id,
            callback=self._on_command,
            event_types=[EventType.COMMAND]
        )
        self._scheduler_task = asyncio.create_task(self._run_scheduler())
        print(f"[{self.agent_id.upper()}] Scheduler agent started")
    
    async def stop(self):
        self._running = False
        if self._scheduler_task:
            self._scheduler_task.cancel()
        self.event_bus.unsubscribe(self.agent_id)
        print(f"[{self.agent_id.upper()}] Scheduler agent stopped")
    
    async def _on_command(self, event: Event):
        if event.target != self.agent_id:
            return
        
        action = event.payload.get("action", "")
        input_text = event.payload.get("input", "")
        
        result = {"message": "Scheduler ready"}
        
        if action == "COMMAND_SCHEDULER":
            if "remind" in input_text.lower():
                result = await self.add_reminder(input_text)
            elif "schedule" in input_text.lower():
                result = await self.schedule_task(input_text)
        
        await self._send_response(event, result)
    
    async def _send_response(self, event: Event, result: Any):
        response_event = Event(
            type=EventType.TASK_COMPLETE,
            source=self.agent_id,
            correlation_id=event.correlation_id,
            payload={
                "task_id": event.payload.get("task_id"),
                "result": result,
                "conversation_id": event.payload.get("conversation_id")
            }
        )
        await self.event_bus.publish(response_event)
    
    async def _run_scheduler(self):
        """Main scheduler loop"""
        while self._running:
            try:
                now = datetime.now()
                for task_id, task in list(self._tasks.items()):
                    if task.enabled and task.next_run and task.next_run <= now:
                        await self._execute_task(task)
                        task.last_run = now
                        task.next_run = self._calculate_next_run(task.schedule)
                
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Scheduler error: {e}")
                await asyncio.sleep(5)
    
    async def _execute_task(self, task: ScheduledTask):
        """Execute a scheduled task"""
        print(f"[{self.agent_id.upper()}] Executing task: {task.name}")
        
        # Publish event for task execution
        event = Event(
            type=EventType.SCHEDULED_TASK,
            source=self.agent_id,
            payload={"task_id": task.id, "action": task.action, "metadata": task.metadata}
        )
        await self.event_bus.publish(event)
    
    def _calculate_next_run(self, schedule: str) -> Optional[datetime]:
        """Calculate next run time from schedule"""
        if schedule == "once":
            return None
        # Simplified - would parse cron expression in production
        return datetime.now() + timedelta(hours=1)
    
    async def add_reminder(self, text: str) -> Dict:
        """Add a reminder"""
        import uuid
        task_id = str(uuid.uuid4())
        
        self._tasks[task_id] = ScheduledTask(
            id=task_id,
            name=f"Reminder: {text[:50]}",
            action="reminder",
            schedule="once",
            next_run=datetime.now() + timedelta(minutes=5),
            metadata={"text": text}
        )
        
        return {"success": True, "message": "Reminder set for 5 minutes", "task_id": task_id}
    
    async def schedule_task(self, text: str) -> Dict:
        """Schedule a recurring task"""
        import uuid
        task_id = str(uuid.uuid4())
        
        self._tasks[task_id] = ScheduledTask(
            id=task_id,
            name=text[:50],
            action="scheduled",
            schedule="hourly",
            next_run=datetime.now() + timedelta(hours=1),
            metadata={"text": text}
        )
        
        return {"success": True, "message": "Task scheduled", "task_id": task_id}
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "running": self._running,
            "capabilities": self.capabilities,
            "active_tasks": len([t for t in self._tasks.values() if t.enabled])
        }


def get_scheduler(event_bus: Optional[EventBus] = None) -> SchedulerAgent:
    global _scheduler_instance
    if '_scheduler_instance' not in globals():
        _scheduler_instance = SchedulerAgent(event_bus)
    return _scheduler_instance


if __name__ == "__main__":
    asyncio.run(SchedulerAgent().start())
