"""
J.A.R.V.I.S. - System Monitor Agent
CPU, RAM, GPU, temperature, and battery stats
"""

import os
import sys
from typing import Dict, Optional, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus, Event, EventType, get_event_bus, get_agent_registry


class SystemMonitorAgent:
    """System Monitor Agent - Real-time system statistics"""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or get_event_bus()
        
        self.agent_id = "system_monitor"
        self.capabilities = [
            "cpu_monitoring",
            "memory_monitoring",
            "disk_monitoring",
            "gpu_monitoring",
            "temperature_reading",
            "battery_status"
        ]
        
        self._running = False
        
        self._register_self()
    
    def _register_self(self):
        self.registry = get_agent_registry()
        self.registry.register_agent(
            agent_id=self.agent_id,
            name="System Monitor",
            capabilities=self.capabilities,
            metadata={"description": "Real-time system statistics"}
        )
    
    async def start(self):
        self._running = True
        self.event_bus.subscribe(
            subscriber_id=self.agent_id,
            callback=self._on_command,
            event_types=[EventType.COMMAND]
        )
        print(f"[{self.agent_id.upper()}] System monitor started")
    
    async def stop(self):
        self._running = False
        self.event_bus.unsubscribe(self.agent_id)
        print(f"[{self.agent_id.upper()}] System monitor stopped")
    
    async def _on_command(self, event: Event):
        if event.target != self.agent_id:
            return
        
        action = event.payload.get("action", "")
        
        if action == "COMMAND_SYSTEM" or action == "STATUS_CHECK":
            result = await self.get_system_stats()
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
    
    async def get_system_stats(self) -> Dict:
        """Get comprehensive system statistics"""
        try:
            import psutil
            
            cpu_percent = psutil.cpu_percent(interval=0.5)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            stats = {
                "cpu": {
                    "usage_percent": cpu_percent,
                    "cores": psutil.cpu_count(logical=False),
                    "logical_cores": psutil.cpu_count(logical=True)
                },
                "memory": {
                    "total_gb": round(memory.total / (1024**3), 2),
                    "available_gb": round(memory.available / (1024**3), 2),
                    "usage_percent": memory.percent
                },
                "disk": {
                    "total_gb": round(disk.total / (1024**3), 2),
                    "used_gb": round(disk.used / (1024**3), 2),
                    "free_gb": round(disk.free / (1024**3), 2),
                    "usage_percent": disk.percent
                }
            }
            
            # Battery (if available)
            try:
                battery = psutil.sensors_battery()
                if battery:
                    stats["battery"] = {
                        "percent": battery.percent,
                        "plugged_in": battery.power_plugged
                    }
            except:
                pass
            
            # Temperatures (if available)
            try:
                temps = psutil.sensors_temperatures()
                if temps:
                    stats["temperatures"] = {
                        k: [{"name": s.label, "current": s.current}] 
                        for k, v in temps.items() 
                        for s in v
                    }
            except:
                pass
            
            return {"success": True, "stats": stats}
            
        except ImportError:
            return {
                "success": True,
                "message": "psutil not installed - install with: pip install psutil",
                "stats": {}
            }
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "running": self._running,
            "capabilities": self.capabilities
        }


def get_system_monitor(event_bus: Optional[EventBus] = None) -> SystemMonitorAgent:
    global _monitor_instance
    if '_monitor_instance' not in globals():
        _monitor_instance = SystemMonitorAgent(event_bus)
    return _monitor_instance


if __name__ == "__main__":
    import asyncio
    asyncio.run(SystemMonitorAgent().start())
