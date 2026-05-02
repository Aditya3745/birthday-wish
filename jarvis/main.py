"""
J.A.R.V.I.S. - Main Entry Point
Just A Rather Very Intelligent System
"""

import os
import sys
import asyncio
import signal
from typing import Optional
from datetime import datetime

# Add jarvis to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from core.brain import Brain, BrainConfig
from core.event_bus import EventBus, Event, EventType, get_event_bus
from core.nlp_engine import IntentClassifier
from core.voice import VoiceModule

# Import agents
from agents.commander import CommanderAgent, get_commander
from agents.memory_agent import MemoryAgent, get_memory
from agents.pc_control import PCControlAgent, get_pc_control
from agents.code_agent import CodeAgent, get_code
from agents.security_agent import SecurityAgent, get_security
from agents.research_agent import ResearchAgent, get_research
from agents.scheduler_agent import SchedulerAgent, get_scheduler
from agents.media_agent import MediaAgent, get_media
from agents.system_monitor import SystemMonitorAgent, get_system_monitor


class JARVIS:
    """
    J.A.R.V.I.S. - Just A Rather Very Intelligent System
    Main orchestrator class
    """
    
    def __init__(self):
        print("=" * 60)
        print("   J.A.R.V.I.S. - Just A Rather Very Intelligent System")
        print("   Version 1.0 - Initializing...")
        print("=" * 60)
        
        # Initialize core components
        self.config = BrainConfig()
        self.brain = Brain(self.config)
        self.event_bus = get_event_bus()
        self.voice = VoiceModule()
        self.intent_classifier = IntentClassifier()
        
        # Agent references
        self.commander: Optional[CommanderAgent] = None
        self.memory: Optional[MemoryAgent] = None
        self.pc_control: Optional[PCControlAgent] = None
        self.code: Optional[CodeAgent] = None
        self.security: Optional[SecurityAgent] = None
        self.research: Optional[ResearchAgent] = None
        self.scheduler: Optional[SchedulerAgent] = None
        self.media: Optional[MediaAgent] = None
        self.system_monitor: Optional[SystemMonitorAgent] = None
        
        self._running = False
    
    async def initialize_agents(self):
        """Initialize all agents"""
        print("\n[INIT] Loading agents...")
        
        # Initialize core agents
        self.commander = get_commander(self.event_bus)
        await self.commander.start()
        
        self.memory = get_memory(self.event_bus)
        await self.memory.start()
        
        # Initialize functional agents
        self.pc_control = get_pc_control(self.event_bus)
        await self.pc_control.start()
        
        self.code = get_code(self.event_bus)
        await self.code.start()
        
        self.security = get_security(self.event_bus)
        await self.security.start()
        
        self.research = get_research(self.event_bus)
        await self.research.start()
        
        self.scheduler = get_scheduler(self.event_bus)
        await self.scheduler.start()
        
        self.media = get_media(self.event_bus)
        await self.media.start()
        
        self.system_monitor = get_system_monitor(self.event_bus)
        await self.system_monitor.start()
        
        print("[INIT] All agents loaded successfully\n")
    
    async def start(self):
        """Start JARVIS"""
        self._running = True
        
        # Start event bus
        await self.event_bus.start()
        
        # Initialize agents
        await self.initialize_agents()
        
        # Subscribe to response events
        self.event_bus.subscribe(
            subscriber_id="main",
            callback=self._on_response,
            event_types=[EventType.RESPONSE]
        )
        
        # Play startup sound/message
        self.voice.speak_async("Good to see you again, sir. All systems online and ready.")
        
        print("\n" + "=" * 60)
        print("   J.A.R.V.I.S. is now ONLINE")
        print("   Type 'quit' or 'exit' to shutdown")
        print("   Say 'Hey JARVIS' for voice mode (placeholder)")
        print("=" * 60 + "\n")
        
        # Main input loop
        await self._run_input_loop()
    
    async def _run_input_loop(self):
        """Main user input loop"""
        while self._running:
            try:
                # Get user input
                user_input = await asyncio.get_event_loop().run_in_executor(
                    None, input, "You: "
                )
                
                user_input = user_input.strip()
                
                if not user_input:
                    continue
                
                # Check for exit commands
                if user_input.lower() in ['quit', 'exit', 'bye', 'goodbye']:
                    break
                
                # Process the input
                await self.process_input(user_input)
                
            except KeyboardInterrupt:
                break
            except EOFError:
                break
    
    async def process_input(self, text: str):
        """Process user input"""
        # Classify intent
        intent_result = self.intent_classifier.classify(text)
        
        print(f"\n[Intent: {intent_result.intent.value} ({intent_result.confidence:.2f})]")
        
        # Create user input event
        event = Event(
            type=EventType.USER_INPUT,
            source="user",
            payload={
                "text": text,
                "conversation_id": "default",
                "timestamp": datetime.now().isoformat()
            }
        )
        
        # Publish to event bus
        await self.event_bus.publish(event)
    
    async def _on_response(self, event: Event):
        """Handle responses from agents"""
        text = event.payload.get("text", "")
        
        if text:
            print(f"\nJARVIS: {text}")
            
            # Speak the response
            self.voice.speak_async(text)
    
    async def stop(self):
        """Shutdown JARVIS"""
        print("\n[SHUTDOWN] Initiating graceful shutdown...")
        
        self._running = False
        
        # Stop all agents
        agents = [
            self.commander, self.memory, self.pc_control,
            self.code, self.security, self.research,
            self.scheduler, self.media, self.system_monitor
        ]
        
        for agent in agents:
            if agent:
                try:
                    await agent.stop()
                except Exception as e:
                    print(f"Error stopping {agent.agent_id}: {e}")
        
        # Stop event bus
        await self.event_bus.stop()
        
        # Farewell message
        self.voice.speak("Shutting down. Goodbye, sir.")
        
        print("\n" + "=" * 60)
        print("   J.A.R.V.I.S. is now OFFLINE")
        print("=" * 60)


async def main():
    """Main entry point"""
    jarvis = JARVIS()
    
    # Setup signal handlers
    loop = asyncio.get_event_loop()
    
    def signal_handler():
        print("\nInterrupt received...")
        jarvis._running = False
    
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, signal_handler)
    
    try:
        await jarvis.start()
    except Exception as e:
        print(f"Fatal error: {e}")
    finally:
        await jarvis.stop()


if __name__ == "__main__":
    asyncio.run(main())
