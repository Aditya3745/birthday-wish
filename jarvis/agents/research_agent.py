"""
J.A.R.V.I.S. - Research Agent
Web search, scraping, and summarization
"""

import os
import sys
from typing import Dict, List, Optional, Any
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus, Event, EventType, get_event_bus, get_agent_registry


class ResearchAgent:
    """Research Agent - Web search and information gathering"""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or get_event_bus()
        
        self.agent_id = "research"
        self.capabilities = [
            "web_search",
            "content_scraping",
            "summarization",
            "news_aggregation",
            "fact_checking"
        ]
        
        self._running = False
        
        self._register_self()
    
    def _register_self(self):
        self.registry = get_agent_registry()
        self.registry.register_agent(
            agent_id=self.agent_id,
            name="Research",
            capabilities=self.capabilities,
            metadata={"description": "Web search and information gathering"}
        )
    
    async def start(self):
        self._running = True
        self.event_bus.subscribe(
            subscriber_id=self.agent_id,
            callback=self._on_command,
            event_types=[EventType.COMMAND]
        )
        print(f"[{self.agent_id.upper()}] Research agent started")
    
    async def stop(self):
        self._running = False
        self.event_bus.unsubscribe(self.agent_id)
        print(f"[{self.agent_id.upper()}] Research agent stopped")
    
    async def _on_command(self, event: Event):
        if event.target != self.agent_id:
            return
        
        action = event.payload.get("action", "")
        input_text = event.payload.get("input", "")
        
        result = {"message": "Research capabilities ready (implement web search integration)"}
        
        if action == "COMMAND_RESEARCH":
            result = await self.search(input_text)
        
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
    
    async def search(self, query: str) -> Dict:
        """Search for information"""
        return {
            "success": True,
            "query": query,
            "results": [],
            "message": "Web search integration pending (add DuckDuckGo/Serper API)"
        }
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "running": self._running,
            "capabilities": self.capabilities
        }


def get_research(event_bus: Optional[EventBus] = None) -> ResearchAgent:
    global _research_instance
    if '_research_instance' not in globals():
        _research_instance = ResearchAgent(event_bus)
    return _research_instance


if __name__ == "__main__":
    asyncio.run(ResearchAgent().start())
