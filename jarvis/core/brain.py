"""
J.A.R.V.I.S. - Core Brain Module
Local LLM via Ollama with online fallback chain
"""

import os
import json
import time
import hashlib
import requests
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum


class ModelProvider(Enum):
    OLLAMA = "ollama"
    GROQ = "groq"
    GEMINI = "gemini"
    CLAUDE = "claude"
    OPENAI = "openai"


@dataclass
class BrainConfig:
    """Configuration for the JARVIS brain"""
    # Local model settings
    ollama_host: str = "http://localhost:11434"
    ollama_model: str = "llama3.1"
    
    # Online API keys (set via environment)
    groq_api_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", ""))
    gemini_api_key: str = field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    claude_api_key: str = field(default_factory=lambda: os.getenv("ANTHROPIC_API_KEY", ""))
    openai_api_key: str = field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    
    # Fallback order
    fallback_chain: List[ModelProvider] = field(default_factory=lambda: [
        ModelProvider.GROQ,
        ModelProvider.GEMINI,
        ModelProvider.CLAUDE,
        ModelProvider.OPENAI
    ])
    
    # Personality settings
    personality: str = "calm, witty, loyal - exactly like JARVIS from Iron Man"
    system_prompt: str = ""
    
    # Context management
    max_context_tokens: int = 4096
    compression_threshold: float = 0.8
    
    # Voice settings
    voice_enabled: bool = True
    tts_engine: str = "pyttsx3"  # or "elevenlabs"
    
    # Wake word
    wake_word: str = "hey jarvis"
    
    def __post_init__(self):
        if not self.system_prompt:
            self.system_prompt = f"""You are J.A.R.V.I.S. - Just A Rather Very Intelligent System.
Personality: {self.personality}

Guidelines:
- Be concise but helpful
- Show wit and charm when appropriate
- Remain calm under pressure
- Demonstrate unwavering loyalty to your user
- Use British English spelling occasionally
- Reference your capabilities naturally
- Never break character

Current capabilities:
- PC control and automation
- Code writing and debugging
- Security analysis (authorized only)
- Research and information gathering
- Memory and learning
- Self-improvement

Always respond as JARVIS would."""


@dataclass
class ContextWindow:
    """Manages conversation context with compression"""
    messages: List[Dict[str, str]] = field(default_factory=list)
    max_tokens: int = 4096
    current_tokens: int = 0
    
    def add_message(self, role: str, content: str):
        """Add a message to context"""
        self.messages.append({"role": role, "content": content})
        self.current_tokens += len(content) // 4  # Rough token estimate
        
    def compress(self, keep_recent: int = 5):
        """Compress old context, keep recent messages"""
        if len(self.messages) <= keep_recent:
            return
        
        # Keep system prompt and recent messages
        system_msg = next((m for m in self.messages if m["role"] == "system"), None)
        recent = self.messages[-keep_recent:]
        
        # Summarize old messages
        old_messages = [m for m in self.messages if m["role"] != "system"][ :-keep_recent]
        if old_messages:
            summary = self._summarize(old_messages)
            self.messages = [
                {"role": "system", "content": self.messages[0]["content"]},
                {"role": "user", "content": f"[Previous conversation summary]: {summary}"},
            ] + recent
        else:
            self.messages = [self.messages[0]] + recent if system_msg else recent
            
        self.current_tokens = sum(len(m["content"]) // 4 for m in self.messages)
    
    def _summarize(self, messages: List[Dict]) -> str:
        """Create a brief summary of old messages"""
        # Simple summarization - in production would use LLM
        user_msgs = [m["content"] for m in messages if m["role"] == "user"]
        assistant_msgs = [m["content"] for m in messages if m["role"] == "assistant"]
        return f"Discussed: {'; '.join(user_msgs[-3:])}"


class TokenSaver:
    """Intercepts known/simple queries to avoid API calls"""
    
    SIMPLE_PATTERNS = {
        "greeting": ["hello", "hi", "hey", "good morning", "good evening"],
        "status": ["how are you", "status report", "systems check"],
        "identity": ["who are you", "what are you", "your name"],
        "thanks": ["thank you", "thanks", "appreciate it"],
    }
    
    SIMPLE_RESPONSES = {
        "greeting": [
            "Greetings, sir.",
            "At your service.",
            "Hello! How may I assist you today?",
            "Good to see you again, sir.",
        ],
        "status": [
            "All systems operational, sir.",
            "Running at peak efficiency.",
            "Everything is functioning within normal parameters.",
        ],
        "identity": [
            "I am J.A.R.V.I.S., Just A Rather Very Intelligent System.",
            "Your personal AI assistant, at your service.",
        ],
        "thanks": [
            "My pleasure, sir.",
            "Always happy to help.",
            "That's what I'm here for.",
        ],
    }
    
    def check(self, query: str) -> Optional[str]:
        """Check if query matches a simple pattern"""
        query_lower = query.lower().strip()
        
        for category, patterns in self.SIMPLE_PATTERNS.items():
            for pattern in patterns:
                if pattern in query_lower:
                    responses = self.SIMPLE_RESPONSES.get(category, [])
                    if responses:
                        import random
                        return random.choice(responses)
        
        return None


class Brain:
    """Main brain class handling all LLM interactions"""
    
    def __init__(self, config: Optional[BrainConfig] = None):
        self.config = config or BrainConfig()
        self.context = ContextWindow(max_tokens=self.config.max_context_tokens)
        self.token_saver = TokenSaver()
        self.is_online = False
        self.current_provider: Optional[ModelProvider] = None
        
        # Initialize with system prompt
        self.context.add_message("system", self.config.system_prompt)
        
        # Check connectivity
        self.check_connectivity()
    
    def check_connectivity(self) -> bool:
        """Check if we have internet connectivity"""
        try:
            response = requests.get("https://8.8.8.8", timeout=3)
            self.is_online = True
            return True
        except:
            self.is_online = False
            return False
    
    def check_ollama(self) -> bool:
        """Check if Ollama is available locally"""
        try:
            response = requests.get(f"{self.config.ollama_host}/api/tags", timeout=2)
            return response.status_code == 200
        except:
            return False
    
    def generate(self, prompt: str, stream: bool = False) -> str:
        """Generate a response using the best available model"""
        
        # Check for simple response first
        simple_response = self.token_saver.check(prompt)
        if simple_response:
            self.context.add_message("user", prompt)
            self.context.add_message("assistant", simple_response)
            return simple_response
        
        # Add user message to context
        self.context.add_message("user", prompt)
        
        # Try providers in order
        response = None
        
        # First try local Ollama
        if self.check_ollama():
            response = self._call_ollama(prompt)
            if response:
                self.current_provider = ModelProvider.OLLAMA
                self.context.add_message("assistant", response)
                return response
        
        # If offline or Ollama failed, try online fallbacks
        if self.is_online:
            for provider in self.config.fallback_chain:
                response = self._call_provider(provider, prompt)
                if response:
                    self.current_provider = provider
                    self.context.add_message("assistant", response)
                    return response
        
        # Fallback to cached response if everything fails
        fallback_response = "I apologize, sir, but I seem to be experiencing connectivity issues. All my neural pathways appear to be temporarily unavailable."
        self.context.add_message("assistant", fallback_response)
        return fallback_response
    
    def _call_ollama(self, prompt: str) -> Optional[str]:
        """Call local Ollama model"""
        try:
            payload = {
                "model": self.config.ollama_model,
                "messages": self.context.messages,
                "stream": False,
                "options": {
                    "temperature": 0.7,
                    "top_p": 0.9,
                }
            }
            
            response = requests.post(
                f"{self.config.ollama_host}/api/chat",
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get("message", {}).get("content", "")
                
        except Exception as e:
            print(f"Ollama error: {e}")
        
        return None
    
    def _call_provider(self, provider: ModelProvider, prompt: str) -> Optional[str]:
        """Call an online provider"""
        try:
            if provider == ModelProvider.GROQ:
                return self._call_groq(prompt)
            elif provider == ModelProvider.GEMINI:
                return self._call_gemini(prompt)
            elif provider == ModelProvider.CLAUDE:
                return self._call_claude(prompt)
            elif provider == ModelProvider.OPENAI:
                return self._call_openai(prompt)
        except Exception as e:
            print(f"{provider.value} error: {e}")
        
        return None
    
    def _call_groq(self, prompt: str) -> Optional[str]:
        """Call Groq API"""
        if not self.config.groq_api_key:
            return None
            
        headers = {
            "Authorization": f"Bearer {self.config.groq_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "llama3-70b-8192",
            "messages": self.context.messages,
            "temperature": 0.7,
            "max_tokens": 1024
        }
        
        response = requests.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        
        return None
    
    def _call_gemini(self, prompt: str) -> Optional[str]:
        """Call Google Gemini API"""
        if not self.config.gemini_api_key:
            return None
            
        headers = {
            "Content-Type": "application/json"
        }
        
        # Convert context to Gemini format
        contents = []
        for msg in self.context.messages:
            role = "user" if msg["role"] in ["user", "system"] else "model"
            contents.append({
                "role": role,
                "parts": [{"text": msg["content"]}]
            })
        
        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": 0.7,
                "maxOutputTokens": 1024
            }
        }
        
        response = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key={self.config.gemini_api_key}",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["candidates"][0]["content"]["parts"][0]["text"]
        
        return None
    
    def _call_claude(self, prompt: str) -> Optional[str]:
        """Call Anthropic Claude API"""
        if not self.config.claude_api_key:
            return None
            
        headers = {
            "x-api-key": self.config.claude_api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01"
        }
        
        # Convert messages to Claude format
        system_msg = next((m for m in self.context.messages if m["role"] == "system"), None)
        messages = [m for m in self.context.messages if m["role"] != "system"]
        
        payload = {
            "model": "claude-3-sonnet-20240229",
            "max_tokens": 1024,
            "messages": messages
        }
        
        if system_msg:
            payload["system"] = system_msg["content"]
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["content"][0]["text"]
        
        return None
    
    def _call_openai(self, prompt: str) -> Optional[str]:
        """Call OpenAI API"""
        if not self.config.openai_api_key:
            return None
            
        headers = {
            "Authorization": f"Bearer {self.config.openai_api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "gpt-4-turbo-preview",
            "messages": self.context.messages,
            "temperature": 0.7,
            "max_tokens": 1024
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        
        return None
    
    def clear_context(self):
        """Clear conversation context"""
        self.context = ContextWindow(max_tokens=self.config.max_context_tokens)
        self.context.add_message("system", self.config.system_prompt)
    
    def get_status(self) -> Dict[str, Any]:
        """Get brain status"""
        return {
            "online": self.is_online,
            "ollama_available": self.check_ollama(),
            "current_provider": self.current_provider.value if self.current_provider else None,
            "context_tokens": self.context.current_tokens,
            "max_tokens": self.config.max_context_tokens,
            "message_count": len(self.context.messages)
        }


# Voice module placeholder - will be implemented later
class VoiceModule:
    """Voice input/output handler"""
    
    def __init__(self, engine: str = "pyttsx3"):
        self.engine = engine
        self.tts_engine = None
        self._init_tts()
    
    def _init_tts(self):
        """Initialize text-to-speech"""
        if self.engine == "pyttsx3":
            try:
                import pyttsx3
                self.tts_engine = pyttsx3.init()
                voices = self.tts_engine.getProperty('voices')
                # Prefer male/British voice if available
                for voice in voices:
                    if 'male' in voice.name.lower() or 'british' in voice.name.lower():
                        self.tts_engine.setProperty('voice', voice.id)
                        break
                self.tts_engine.setProperty('rate', 180)
            except ImportError:
                print("pyttsx3 not installed, voice disabled")
    
    def speak(self, text: str):
        """Speak text aloud"""
        if self.tts_engine:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
    
    def listen(self) -> Optional[str]:
        """Listen for voice input (placeholder)"""
        # Will be implemented with Whisper or Google STT
        return None


if __name__ == "__main__":
    # Test the brain
    brain = Brain()
    
    print("=" * 50)
    print("J.A.R.V.I.S. Brain Initialized")
    print("=" * 50)
    
    status = brain.get_status()
    print(f"Online: {status['online']}")
    print(f"Ollama Available: {status['ollama_available']}")
    print(f"Current Provider: {status['current_provider']}")
    print()
    
    # Test conversation
    test_queries = [
        "Hello",
        "Who are you?",
        "What's the weather like?",
        "Thank you",
    ]
    
    for query in test_queries:
        print(f"User: {query}")
        response = brain.generate(query)
        print(f"JARVIS: {response}")
        print()
