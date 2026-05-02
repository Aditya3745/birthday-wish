"""
J.A.R.V.I.S. - NLP Engine Module
Intent classification and natural language understanding
"""

import re
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import json


class Intent(Enum):
    """Supported intents in the system"""
    GREETING = "greeting"
    FAREWELL = "farewell"
    QUESTION = "question"
    COMMAND_PC = "command_pc"
    COMMAND_CODE = "command_code"
    COMMAND_SECURITY = "command_security"
    COMMAND_RESEARCH = "command_research"
    COMMAND_MEDIA = "command_media"
    COMMAND_SCHEDULER = "command_scheduler"
    COMMAND_FILE = "command_file"
    COMMAND_SYSTEM = "command_system"
    MEMORY_QUERY = "memory_query"
    MEMORY_STORE = "memory_store"
    STATUS_CHECK = "status_check"
    HELP = "help"
    UNKNOWN = "unknown"


@dataclass
class IntentResult:
    """Result of intent classification"""
    intent: Intent
    confidence: float
    entities: Dict[str, Any] = field(default_factory=dict)
    original_text: str = ""
    
    def to_dict(self) -> Dict:
        return {
            "intent": self.intent.value,
            "confidence": self.confidence,
            "entities": self.entities,
            "original_text": self.original_text
        }


class IntentClassifier:
    """
    Rule-based intent classifier with pattern matching.
    In production, this would use a trained ML model.
    """
    
    PATTERNS: Dict[Intent, List[str]] = {
        Intent.GREETING: [
            r"\b(hi|hello|hey|greetings|good morning|good afternoon|good evening)\b",
            r"\bhowdy\b", r"\bsup\b", r"\bwhat's up\b"
        ],
        Intent.FAREWELL: [
            r"\b(bye|goodbye|see you|later|quit|exit)\b",
            r"\bgotta go\b", r"\bleaving\b"
        ],
        Intent.QUESTION: [
            r"\b(what|who|when|where|why|how|which)\b.*\?",
            r"\bcould you tell me\b", r"\bdo you know\b"
        ],
        Intent.COMMAND_PC: [
            r"\b(open|close|start|launch|kill|stop)\s+\w+",
            r"\bclick\s+(on|at)\b", r"\btype\b", r"\bpress\s+(key|button)\b",
            r"\bmove\s+mouse\b", r"\bscroll\b", r"\bminimize|maximize\b",
            r"\bresize\s+window\b", r"\bswitch\s+(to|tab)\b",
            r"\bshow\s+desktop\b", r"\block\s+screen\b"
        ],
        Intent.COMMAND_CODE: [
            r"\b(write|create|code|program|develop|build)\s+(a|an|some)?\s*\w*\s*(code|script|program|app|function)",
            r"\b(run|execute|test|debug)\s+(the)?\s*\w*\s*(code|script|program|test)",
            r"\bfix\s+(this|the)\s*(bug|error|issue)",
            r"\brefactor\b", r"\boptimize\b", r"\bimprove\s+(the)?\s*code",
            r"\bgenerate\s+(a|some)?\s*\w*\s*(code|function|class|module)",
            r"\bexplain\s+(this|the)?\s*code", r"\breview\s+(my|the)?\s*code"
        ],
        Intent.COMMAND_SECURITY: [
            r"\b(scan|audit|check)\s+(for)?\s*(vulnerabilities|security|ports)",
            r"\bpentest\b", r"\bpenetration\s+test\b",
            r"\bnetwork\s+(scan|recon|discovery)",
            r"\bcheck\s+(firewall|ports|services)",
            r"\bwifi\s+(audit|scan|crack)", r"\bwpa\b", r"\bwps\b",
            r"\bfind\s+(vulnerabilities|weaknesses|exploits)"
        ],
        Intent.COMMAND_RESEARCH: [
            r"\b(search|find|look up|google)\s+.+",
            r"\bresearch\b", r"\bsummarize\b", r"\bget\s+information",
            r"\bwhat's?\s+(new|latest|trending)", r"\bnews\b",
            r"\bfetch\s+(data|info|articles)", r"\bscrape\b"
        ],
        Intent.COMMAND_MEDIA: [
            r"\b(play|pause|stop|skip|next|previous)\s*(music|video|song|track)?",
            r"\b(volume|mute|unmute)\b", r"\bturn\s+(up|down)\s+(the)?\s*volume",
            r"\bshuffle\b", r"\brepeat\b", r"\bplaylist\b",
            r"\byoutube\b", r"\bspotify\b", r"\bplay\s+me\s+"
        ],
        Intent.COMMAND_SCHEDULER: [
            r"\b(remind|schedule|set\s+(up|)|create)\s+(a)?\s*(reminder|alarm|event|task)",
            r"\badd\s+to\s+calendar\b", r"\bset\s+an?\s+alarm",
            r"\bwhen\s+is\b", r"\bwhat's\s+on\s+my\s+schedule",
            r"\bcron\b", r"\bautomate\b"
        ],
        Intent.COMMAND_FILE: [
            r"\b(create|delete|move|copy|rename|open)\s+(file|folder|directory)",
            r"\blist\s+(files|directory|contents)", r"\bsearch\s+files",
            r"\borganize\s+(files|folder)", r"\bclean\s+up\b",
            r"\bdownload\b", r"\bupload\b", r"\bextract\b", r"\bcompress\b"
        ],
        Intent.COMMAND_SYSTEM: [
            r"\b(system|cpu|ram|memory|disk|gpu|temperature|battery)\s*(stats|status|usage|info)?",
            r"\bperformance\b", r"\bmonitor\b", r"\bresource\b",
            r"\bhow\s+much\s+(ram|cpu|disk|memory)", r"\bwhat's\s+my\s+(pc|system|computer)"
        ],
        Intent.MEMORY_QUERY: [
            r"\b(do you remember|recall|what did i|did i)\s+.+",
            r"\bmy\s+(notes|preferences|settings|history)",
            r"\bsearch\s+memory\b", r"\bfind\s+in\s+memory",
            r"\bwhat\s+do\s+you\s+know\s+about\s+me"
        ],
        Intent.MEMORY_STORE: [
            r"\b(remember|save|store|note|learn)\s+(that)?\s*.+",
            r"\bdon't\s+forget\b", r"\bmake\s+a\s+note",
            r"\badd\s+to\s+memory\b", r"\bupdate\s+(your)?\s*memory"
        ],
        Intent.STATUS_CHECK: [
            r"\b(status|health|diagnostic|check)\s+(system|all|everything)?",
            r"\bare\s+you\s+(ok|okay|working|online)",
            r"\breport\b", r"\bwhat's\s+your\s+status"
        ],
        Intent.HELP: [
            r"\b(help|support|assist|guide)\b",
            r"\bwhat\s+can\s+you\s+do\b", r"\bcapabilities\b",
            r"\bhow\s+do\s+i\b", r"\bhow\s+to\b"
        ]
    }
    
    ENTITY_PATTERNS: Dict[str, List[Tuple[str, str]]] = {
        "application": [
            (r"\b(chrome|firefox|edge|safari|brave)\b", "browser"),
            (r"\b(vs code|visual studio|sublime|atom|notepad)\b", "editor"),
            (r"\b(terminal|cmd|powershell|bash|zsh)\b", "terminal"),
            (r"\b(excel|word|powerpoint|photoshop|illustrator)\b", "productivity"),
        ],
        "action": [
            (r"\b(open|launch|start)\b", "open"),
            (r"\b(close|kill|stop|quit|exit)\b", "close"),
            (r"\b(click|press|tap)\b", "click"),
            (r"\b(type|write|input)\b", "type"),
            (r"\b(copy|duplicate)\b", "copy"),
            (r"\b(cut|remove|delete)\b", "delete"),
            (r"\b(paste|insert)\b", "paste"),
        ],
        "time": [
            (r"\b(in\s+\d+\s*(minute|hour|day|week)s?)\b", "relative"),
            (r"\b(at\s+\d{1,2}:\d{2}\s*(am|pm)?)\b", "absolute"),
            (r"\b(on\s+(monday|tuesday|wednesday|thursday|friday|saturday|sunday))\b", "day"),
            (r"\b(today|tomorrow|yesterday|now|later)\b", "keyword"),
        ],
        "file_type": [
            (r"\b(\.(txt|pdf|doc|docx|xls|xlsx|py|js|html|css|json|xml|csv))\b", "extension"),
            (r"\b(image|photo|picture|jpg|png|gif)\b", "image"),
            (r"\b(video|movie|mp4|avi|mkv)\b", "video"),
            (r"\b(audio|music|song|mp3|wav|flac)\b", "audio"),
        ],
        "location": [
            (r"\b(on\s+(desktop|documents|downloads|pictures|videos|music))\b", "folder"),
            (r"\b(in\s+[A-Z]:\\[^\\]+)\b", "windows_path"),
            (r"\b(/[\w/]+)\b", "unix_path"),
        ]
    }
    
    def classify(self, text: str) -> IntentResult:
        """Classify the intent of the input text"""
        text_lower = text.lower().strip()
        
        best_intent = Intent.UNKNOWN
        best_confidence = 0.0
        best_match_count = 0
        
        for intent, patterns in self.PATTERNS.items():
            match_count = 0
            total_pattern_score = 0.0
            
            for pattern in patterns:
                if re.search(pattern, text_lower):
                    match_count += 1
                    # Weight longer matches higher
                    total_pattern_score += len(pattern) / 100.0
            
            if match_count > 0:
                # Calculate confidence based on match count and pattern scores
                confidence = min(1.0, (match_count * 0.3) + (total_pattern_score * 0.1))
                
                if confidence > best_confidence:
                    best_confidence = confidence
                    best_intent = intent
                    best_match_count = match_count
        
        # Extract entities
        entities = self._extract_entities(text_lower)
        
        # Boost confidence if we have relevant entities
        if entities and best_intent != Intent.UNKNOWN:
            best_confidence = min(1.0, best_confidence + 0.1)
        
        return IntentResult(
            intent=best_intent,
            confidence=best_confidence,
            entities=entities,
            original_text=text
        )
    
    def _extract_entities(self, text: str) -> Dict[str, Any]:
        """Extract entities from the text"""
        entities = {}
        
        for entity_type, patterns in self.ENTITY_PATTERNS.items():
            matches = []
            for pattern, category in patterns:
                match = re.search(pattern, text)
                if match:
                    matches.append({
                        "text": match.group(),
                        "category": category,
                        "start": match.start(),
                        "end": match.end()
                    })
            
            if matches:
                entities[entity_type] = matches
        
        # Extract quoted text as special entity
        quoted = re.findall(r'"([^"]+)"|\'([^\']+)\'', text)
        if quoted:
            entities["quoted_text"] = [q[0] or q[1] for q in quoted]
        
        # Extract numbers
        numbers = re.findall(r'\b\d+(?:\.\d+)?\b', text)
        if numbers:
            entities["numbers"] = [float(n) for n in numbers]
        
        return entities
    
    def get_suggested_agents(self, intent_result: IntentResult) -> List[str]:
        """Get list of agents that can handle this intent"""
        intent_agent_map = {
            Intent.GREETING: ["commander"],
            Intent.FAREWELL: ["commander"],
            Intent.QUESTION: ["commander", "research"],
            Intent.COMMAND_PC: ["pc_control"],
            Intent.COMMAND_CODE: ["code"],
            Intent.COMMAND_SECURITY: ["security"],
            Intent.COMMAND_RESEARCH: ["research"],
            Intent.COMMAND_MEDIA: ["media"],
            Intent.COMMAND_SCHEDULER: ["scheduler"],
            Intent.COMMAND_FILE: ["file_manager"],
            Intent.COMMAND_SYSTEM: ["system_monitor"],
            Intent.MEMORY_QUERY: ["memory"],
            Intent.MEMORY_STORE: ["memory"],
            Intent.STATUS_CHECK: ["system_monitor", "commander"],
            Intent.HELP: ["commander"],
            Intent.UNKNOWN: ["commander"]
        }
        
        return intent_agent_map.get(intent_result.intent, ["commander"])


class CommandParser:
    """Parse natural language commands into structured actions"""
    
    ACTION_VERBS = {
        "open": "OPEN",
        "launch": "OPEN",
        "start": "OPEN",
        "close": "CLOSE",
        "kill": "CLOSE",
        "quit": "CLOSE",
        "exit": "CLOSE",
        "click": "CLICK",
        "double-click": "DOUBLE_CLICK",
        "right-click": "RIGHT_CLICK",
        "type": "TYPE",
        "write": "TYPE",
        "press": "PRESS_KEY",
        "move": "MOVE_MOUSE",
        "scroll": "SCROLL",
        "select": "SELECT",
        "highlight": "SELECT",
        "copy": "COPY",
        "cut": "CUT",
        "paste": "PASTE",
        "delete": "DELETE",
        "remove": "DELETE",
        "create": "CREATE",
        "make": "CREATE",
        "save": "SAVE",
        "load": "LOAD",
        "run": "RUN",
        "execute": "RUN",
        "test": "TEST",
        "debug": "DEBUG",
        "search": "SEARCH",
        "find": "FIND",
        "replace": "REPLACE",
    }
    
    def parse_command(self, text: str) -> Dict[str, Any]:
        """Parse a command string into structured format"""
        text_lower = text.lower().strip()
        words = text_lower.split()
        
        result = {
            "action": None,
            "target": None,
            "parameters": {},
            "raw": text
        }
        
        # Find action verb
        for word in words:
            if word in self.ACTION_VERBS:
                result["action"] = self.ACTION_VERBS[word]
                break
        
        # If no action found, try multi-word actions
        if not result["action"]:
            for i in range(len(words) - 1):
                phrase = f"{words[i]}-{words[i+1]}"
                if phrase in self.ACTION_VERBS:
                    result["action"] = self.ACTION_VERBS[phrase]
                    break
        
        # Extract target (usually after the verb)
        if result["action"]:
            action_word = None
            for word in words:
                if word in self.ACTION_VERBS or f"{word}" in [f"{k}" for k in self.ACTION_VERBS.keys()]:
                    action_word = word
                    break
            
            if action_word:
                idx = words.index(action_word) if action_word in words else 0
                target_words = words[idx + 1:]
                
                # Remove common filler words
                fillers = ["the", "a", "an", "my", "this", "that", "for", "me", "please", "can", "you", "could", "would"]
                target_words = [w for w in target_words if w not in fillers]
                
                if target_words:
                    result["target"] = " ".join(target_words).rstrip("?.!")
        
        # Extract parameters
        result["parameters"] = self._extract_parameters(text_lower)
        
        return result
    
    def _extract_parameters(self, text: str) -> Dict[str, Any]:
        """Extract parameters from command text"""
        params = {}
        
        # Check for specific parameter patterns
        time_match = re.search(r'for\s+(\d+)\s*(minute|hour|second|day|week)s?', text)
        if time_match:
            params["duration"] = {
                "value": int(time_match.group(1)),
                "unit": time_match.group(2)
            }
        
        count_match = re.search(r'(\d+)\s*(times|times?)', text)
        if count_match:
            params["repeat"] = int(count_match.group(1))
        
        location_match = re.search(r'(?:at|to|in|on)\s+(.+?)(?:\s|$)', text)
        if location_match:
            params["location"] = location_match.group(1).strip()
        
        # Check for key names
        key_match = re.search(r'(?:key|button)\s+[\'"]?([A-Za-z0-9]+)[\'"]?', text)
        if key_match:
            params["key"] = key_match.group(1)
        
        # Check for coordinates
        coord_match = re.search(r'(\d+)[,\s]+(\d+)', text)
        if coord_match:
            params["coordinates"] = {
                "x": int(coord_match.group(1)),
                "y": int(coord_match.group(2))
            }
        
        return params


if __name__ == "__main__":
    # Test the NLP engine
    classifier = IntentClassifier()
    parser = CommandParser()
    
    test_queries = [
        "Hello JARVIS",
        "Open Chrome browser",
        "Write a Python script to calculate fibonacci",
        "Scan my network for vulnerabilities",
        "Play some music",
        "Remind me to call John at 3pm",
        "What's my CPU usage?",
        "Remember that I like coffee",
        "Search for latest AI news",
        "Create a new folder called Projects",
    ]
    
    print("=" * 60)
    print("J.A.R.V.I.S. NLP Engine Test")
    print("=" * 60)
    
    for query in test_queries:
        print(f"\nQuery: {query}")
        
        # Classify intent
        result = classifier.classify(query)
        print(f"  Intent: {result.intent.value} ({result.confidence:.2f})")
        print(f"  Entities: {json.dumps(result.entities, indent=4)}")
        print(f"  Suggested Agents: {classifier.get_suggested_agents(result)}")
        
        # Parse command
        parsed = parser.parse_command(query)
        print(f"  Parsed Action: {parsed['action']}")
        print(f"  Target: {parsed['target']}")
        print(f"  Parameters: {parsed['parameters']}")
