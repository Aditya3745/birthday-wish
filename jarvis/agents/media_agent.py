"""
J.A.R.V.I.S. - Media Agent
Music, video, and YouTube control
"""

import os
import sys
from typing import Dict, Optional, Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus, Event, EventType, get_event_bus, get_agent_registry


class MediaAgent:
    """Media Agent - Controls music, video, and media playback"""
    
    def __init__(self, event_bus: Optional[EventBus] = None):
        self.event_bus = event_bus or get_event_bus()
        
        self.agent_id = "media"
        self.capabilities = [
            "music_playback",
            "video_control",
            "youtube_integration",
            "volume_control",
            "playlist_management"
        ]
        
        self._running = False
        self._current_track = None
        self._is_playing = False
        
        self._register_self()
    
    def _register_self(self):
        self.registry = get_agent_registry()
        self.registry.register_agent(
            agent_id=self.agent_id,
            name="Media Controller",
            capabilities=self.capabilities,
            metadata={"description": "Music and video playback control"}
        )
    
    async def start(self):
        self._running = True
        self.event_bus.subscribe(
            subscriber_id=self.agent_id,
            callback=self._on_command,
            event_types=[EventType.COMMAND]
        )
        print(f"[{self.agent_id.upper()}] Media agent started")
    
    async def stop(self):
        self._running = False
        self.event_bus.unsubscribe(self.agent_id)
        print(f"[{self.agent_id.upper()}] Media agent stopped")
    
    async def _on_command(self, event: Event):
        if event.target != self.agent_id:
            return
        
        action = event.payload.get("action", "")
        input_text = event.payload.get("input", "")
        
        result = {"message": "Media controls ready"}
        
        if action == "COMMAND_MEDIA":
            if "play" in input_text.lower():
                result = await self.play(input_text)
            elif "pause" in input_text.lower():
                result = await self.pause()
            elif "stop" in input_text.lower():
                result = await self.stop_media()
            elif "volume" in input_text.lower():
                result = await self.set_volume(input_text)
        
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
    
    async def play(self, query: str) -> Dict:
        """Play media"""
        self._is_playing = True
        self._current_track = query
        return {"success": True, "message": f"Playing: {query}", "track": query}
    
    async def pause(self) -> Dict:
        """Pause playback"""
        self._is_playing = False
        return {"success": True, "message": "Playback paused"}
    
    async def stop_media(self) -> Dict:
        """Stop playback"""
        self._is_playing = False
        self._current_track = None
        return {"success": True, "message": "Playback stopped"}
    
    async def set_volume(self, text: str) -> Dict:
        """Set volume level"""
        return {"success": True, "message": f"Volume adjusted: {text}"}
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "agent_id": self.agent_id,
            "running": self._running,
            "capabilities": self.capabilities,
            "currently_playing": self._current_track,
            "is_playing": self._is_playing
        }


def get_media(event_bus: Optional[EventBus] = None) -> MediaAgent:
    global _media_instance
    if '_media_instance' not in globals():
        _media_instance = MediaAgent(event_bus)
    return _media_instance


if __name__ == "__main__":
    asyncio.run(MediaAgent().start())
