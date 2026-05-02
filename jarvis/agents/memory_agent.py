"""
J.A.R.V.I.S. - Memory Agent
Persistent memory system with SQLite + FAISS
"""

import os
import json
import sqlite3
import hashlib
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from datetime import datetime
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.event_bus import EventBus, Event, EventType, get_event_bus, get_agent_registry


# Try to import faiss, make it optional
try:
    import faiss
    FAISS_AVAILABLE = True
except ImportError:
    FAISS_AVAILABLE = False
    print("FAISS not available, semantic search disabled")


@dataclass
class MemoryEntry:
    """Represents a single memory entry"""
    id: str
    content: str
    memory_type: str  # episodic, semantic, personal, fact, skill
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: Optional[datetime] = None
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "content": self.content,
            "memory_type": self.memory_type,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class MemoryDatabase:
    """SQLite database for structured memory storage"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize the database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Episodic memory (conversations, events)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS episodic (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                role TEXT,
                conversation_id TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                summary TEXT
            )
        """)
        
        # Personal information (encrypted in production)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS personal (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                category TEXT,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Facts (world knowledge, user facts)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id TEXT PRIMARY KEY,
                content TEXT NOT NULL,
                source TEXT,
                confidence REAL DEFAULT 1.0,
                verified BOOLEAN DEFAULT FALSE,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Skills (learned procedures)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS skills (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                code TEXT,
                parameters TEXT,
                examples TEXT,
                usage_count INTEGER DEFAULT 0,
                last_used DATETIME,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Indexes for faster queries
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_episodic_timestamp ON episodic(timestamp)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_personal_category ON personal(category)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_facts_source ON facts(source)")
        
        conn.commit()
        conn.close()
    
    def store_episodic(self, entry: MemoryEntry):
        """Store an episodic memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO episodic (id, content, role, conversation_id, timestamp, summary)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entry.id,
            entry.content,
            entry.metadata.get("role", ""),
            entry.metadata.get("conversation_id", ""),
            entry.created_at.isoformat(),
            entry.metadata.get("summary", "")
        ))
        
        conn.commit()
        conn.close()
    
    def get_episodic(self, limit: int = 50, conversation_id: Optional[str] = None) -> List[Dict]:
        """Retrieve episodic memories"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if conversation_id:
            cursor.execute("""
                SELECT id, content, role, conversation_id, timestamp, summary
                FROM episodic
                WHERE conversation_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (conversation_id, limit))
        else:
            cursor.execute("""
                SELECT id, content, role, conversation_id, timestamp, summary
                FROM episodic
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "content": row[1],
                "role": row[2],
                "conversation_id": row[3],
                "timestamp": row[4],
                "summary": row[5]
            })
        
        conn.close()
        return results
    
    def store_personal(self, key: str, value: Any, category: str = "general"):
        """Store personal information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO personal (key, value, category, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        """, (key, json.dumps(value), category))
        
        conn.commit()
        conn.close()
    
    def get_personal(self, key: Optional[str] = None, category: Optional[str] = None) -> Dict:
        """Retrieve personal information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if key:
            cursor.execute("SELECT key, value FROM personal WHERE key = ?", (key,))
            row = cursor.fetchone()
            conn.close()
            return {row[0]: json.loads(row[1])} if row else {}
        
        elif category:
            cursor.execute("SELECT key, value FROM personal WHERE category = ?", (category,))
        else:
            cursor.execute("SELECT key, value FROM personal")
        
        results = {}
        for row in cursor.fetchall():
            results[row[0]] = json.loads(row[1])
        
        conn.close()
        return results
    
    def delete_personal(self, key: str):
        """Delete personal information"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM personal WHERE key = ?", (key,))
        conn.commit()
        conn.close()
    
    def store_fact(self, entry: MemoryEntry, source: str = "user"):
        """Store a fact"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO facts (id, content, source, confidence, verified, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            entry.id,
            entry.content,
            source,
            entry.metadata.get("confidence", 1.0),
            entry.metadata.get("verified", False),
            entry.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_facts(self, query: Optional[str] = None, limit: int = 50) -> List[Dict]:
        """Retrieve facts"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if query:
            cursor.execute("""
                SELECT id, content, source, confidence, verified, created_at
                FROM facts
                WHERE content LIKE ?
                ORDER BY confidence DESC, created_at DESC
                LIMIT ?
            """, (f"%{query}%", limit))
        else:
            cursor.execute("""
                SELECT id, content, source, confidence, verified, created_at
                FROM facts
                ORDER BY created_at DESC
                LIMIT ?
            """, (limit,))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "content": row[1],
                "source": row[2],
                "confidence": row[3],
                "verified": bool(row[4]),
                "created_at": row[5]
            })
        
        conn.close()
        return results
    
    def store_skill(self, entry: MemoryEntry):
        """Store a learned skill"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT OR REPLACE INTO skills 
            (id, name, description, code, parameters, examples, usage_count, last_used, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            entry.id,
            entry.metadata.get("name", ""),
            entry.content,
            entry.metadata.get("code", ""),
            json.dumps(entry.metadata.get("parameters", [])),
            json.dumps(entry.metadata.get("examples", [])),
            entry.metadata.get("usage_count", 0),
            entry.metadata.get("last_used"),
            entry.created_at.isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_skill(self, name: Optional[str] = None) -> List[Dict]:
        """Retrieve skills"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if name:
            cursor.execute("""
                SELECT id, name, description, code, parameters, examples, usage_count, last_used
                FROM skills
                WHERE name LIKE ?
            """, (f"%{name}%",))
        else:
            cursor.execute("""
                SELECT id, name, description, code, parameters, examples, usage_count, last_used
                FROM skills
                ORDER BY usage_count DESC
            """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "id": row[0],
                "name": row[1],
                "description": row[2],
                "code": row[3],
                "parameters": json.loads(row[4]),
                "examples": json.loads(row[5]),
                "usage_count": row[6],
                "last_used": row[7]
            })
        
        conn.close()
        return results


class SemanticIndex:
    """FAISS-based semantic search index"""
    
    def __init__(self, index_path: str, dimension: int = 384):
        self.index_path = index_path
        self.dimension = dimension
        self.index = None
        self.documents: Dict[int, str] = {}
        self.document_ids: Dict[str, int] = {}
        
        if FAISS_AVAILABLE:
            self._load_or_create_index()
    
    def _load_or_create_index(self):
        """Load existing index or create new one"""
        if os.path.exists(self.index_path):
            try:
                self.index = faiss.read_index(self.index_path)
                # Load document mappings
                meta_path = self.index_path + ".meta"
                if os.path.exists(meta_path):
                    with open(meta_path, "r") as f:
                        data = json.load(f)
                        self.documents = {int(k): v for k, v in data["documents"].items()}
                        self.document_ids = data["document_ids"]
            except Exception as e:
                print(f"Error loading index: {e}")
                self._create_index()
        else:
            self._create_index()
    
    def _create_index(self):
        """Create a new index"""
        # Using L2 distance (Euclidean)
        self.index = faiss.IndexFlatL2(self.dimension)
    
    def _get_embedding(self, text: str) -> List[float]:
        """Get embedding for text (placeholder - would use sentence transformer)"""
        # In production, use: from sentence_transformers import SentenceTransformer
        # model = SentenceTransformer('all-MiniLM-L6-v2')
        # embedding = model.encode(text)
        
        # Placeholder: random embedding (for testing only)
        import random
        return [random.gauss(0, 1) for _ in range(self.dimension)]
    
    def add(self, doc_id: str, text: str):
        """Add a document to the index"""
        if not FAISS_AVAILABLE:
            return
        
        embedding = self._get_embedding(text)
        embedding_array = [[embedding]]
        
        # Add to FAISS index
        self.index.add(embedding_array)
        
        # Store mapping
        idx = len(self.documents)
        self.documents[idx] = text
        self.document_ids[doc_id] = idx
        
        self._save()
    
    def search(self, query: str, k: int = 5) -> List[Tuple[str, float]]:
        """Search for similar documents"""
        if not FAISS_AVAILABLE or self.index.ntotal == 0:
            return []
        
        query_embedding = self._get_embedding(query)
        query_array = [[query_embedding]]
        
        # Search
        distances, indices = self.index.search(query_array, k)
        
        results = []
        for i, idx in enumerate(indices[0]):
            if idx >= 0 and idx in self.documents:
                doc_id = next((k for k, v in self.document_ids.items() if v == idx), None)
                results.append((doc_id or str(idx), float(distances[0][i])))
        
        return results
    
    def _save(self):
        """Save index to disk"""
        if not FAISS_AVAILABLE:
            return
        
        faiss.write_index(self.index, self.index_path)
        
        # Save document mappings
        meta_path = self.index_path + ".meta"
        with open(meta_path, "w") as f:
            json.dump({
                "documents": self.documents,
                "document_ids": self.document_ids
            }, f)


class MemoryAgent:
    """
    Memory Agent - Handles all memory operations
    Stores and retrieves information using SQLite + FAISS
    """
    
    def __init__(self, event_bus: Optional[EventBus] = None, memory_dir: str = "memory"):
        self.event_bus = event_bus or get_event_bus()
        self.memory_dir = memory_dir
        
        # Ensure memory directory exists
        os.makedirs(memory_dir, exist_ok=True)
        
        self.agent_id = "memory"
        self.capabilities = [
            "episodic_memory",
            "semantic_search",
            "personal_data_storage",
            "fact_storage",
            "skill_learning",
            "memory_deduplication"
        ]
        
        # Initialize databases
        self.episodic_db = MemoryDatabase(os.path.join(memory_dir, "episodic.db"))
        self.semantic_index = SemanticIndex(os.path.join(memory_dir, "semantic.index"))
        
        # Personal data file (would be encrypted in production)
        self.personal_file = os.path.join(memory_dir, "personal.json")
        self._personal_data = self._load_personal_data()
        
        self._running = False
        
        # Register with the system
        self._register_self()
    
    def _register_self(self):
        """Register memory agent with the registry"""
        self.registry = get_agent_registry()
        self.registry.register_agent(
            agent_id=self.agent_id,
            name="Memory",
            capabilities=self.capabilities,
            metadata={
                "description": "Persistent memory storage and retrieval",
                "priority": 2
            }
        )
    
    def _load_personal_data(self) -> Dict:
        """Load personal data from file"""
        if os.path.exists(self.personal_file):
            with open(self.personal_file, "r") as f:
                return json.load(f)
        return {}
    
    def _save_personal_data(self):
        """Save personal data to file"""
        with open(self.personal_file, "w") as f:
            json.dump(self._personal_data, f, indent=2)
    
    async def start(self):
        """Start the memory agent"""
        self._running = True
        
        # Subscribe to memory events
        self.event_bus.subscribe(
            subscriber_id=self.agent_id,
            callback=self._on_memory_command,
            event_types=[EventType.COMMAND]
        )
        
        print(f"[{self.agent_id.upper()}] Memory agent started")
    
    async def stop(self):
        """Stop the memory agent"""
        self._running = False
        self.event_bus.unsubscribe(self.agent_id)
        print(f"[{self.agent_id.upper()}] Memory agent stopped")
    
    async def _on_memory_command(self, event: Event):
        """Handle memory commands"""
        if event.target != self.agent_id:
            return
        
        action = event.payload.get("action", "")
        
        if action in ["memory_query", "search_memory"]:
            query = event.payload.get("input", "")
            results = await self.search(query)
            await self._send_response(event, results)
        
        elif action in ["memory_store", "remember"]:
            content = event.payload.get("input", "")
            memory_type = event.payload.get("memory_type", "episodic")
            await self.store(content, memory_type=memory_type)
            await self._send_response(event, {"message": "I've made a note of that, sir."})
        
        elif action == "get_personal":
            key = event.payload.get("key")
            data = self.get_personal(key)
            await self._send_response(event, data)
        
        elif action == "set_personal":
            key = event.payload.get("key")
            value = event.payload.get("value")
            self.set_personal(key, value)
            await self._send_response(event, {"message": "Personal data updated."})
    
    async def _send_response(self, event: Event, result: Any):
        """Send response back through event bus"""
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
    
    def store(self, content: str, memory_type: str = "episodic", 
              metadata: Optional[Dict] = None) -> MemoryEntry:
        """Store a memory"""
        import uuid
        
        # Check for duplicates
        if self._is_duplicate(content):
            print(f"[{self.agent_id.upper()}] Duplicate memory detected, skipping")
            return None
        
        entry = MemoryEntry(
            id=str(uuid.uuid4()),
            content=content,
            memory_type=memory_type,
            metadata=metadata or {},
        )
        
        # Store based on type
        if memory_type == "episodic":
            self.episodic_db.store_episodic(entry)
        elif memory_type == "personal":
            key = metadata.get("key", entry.id)
            self.set_personal(key, content)
        elif memory_type == "fact":
            self.episodic_db.store_fact(entry)
        elif memory_type == "skill":
            self.episodic_db.store_skill(entry)
        
        # Add to semantic index
        self.semantic_index.add(entry.id, content)
        
        print(f"[{self.agent_id.upper()}] Stored {memory_type} memory: {entry.id}")
        return entry
    
    def _is_duplicate(self, content: str, threshold: float = 0.95) -> bool:
        """Check if content is a duplicate"""
        # Simple hash-based deduplication
        content_hash = hashlib.md5(content.encode()).hexdigest()
        
        # Check against recent memories
        recent = self.episodic_db.get_episodic(limit=100)
        for memory in recent:
            memory_hash = hashlib.md5(memory["content"].encode()).hexdigest()
            if content_hash == memory_hash:
                return True
        
        return False
    
    async def search(self, query: str, memory_type: Optional[str] = None, 
                     limit: int = 10) -> List[Dict]:
        """Search memories"""
        results = []
        
        # Semantic search
        semantic_results = self.semantic_index.search(query, k=limit)
        
        for doc_id, score in semantic_results:
            results.append({
                "id": doc_id,
                "content": self.semantic_index.documents.get(doc_id, ""),
                "score": score,
                "type": "semantic"
            })
        
        # Also search episodic database
        if not memory_type or memory_type == "episodic":
            episodic = self.episodic_db.get_episodic(limit=limit)
            for mem in episodic:
                if query.lower() in mem["content"].lower():
                    results.append({
                        **mem,
                        "type": "episodic"
                    })
        
        # Search facts
        if not memory_type or memory_type == "fact":
            facts = self.episodic_db.get_facts(query=query, limit=limit)
            for fact in facts:
                results.append({
                    **fact,
                    "type": "fact"
                })
        
        return results[:limit]
    
    def get_personal(self, key: Optional[str] = None) -> Dict:
        """Get personal data"""
        if key:
            return self._personal_data.get(key, {})
        return self._personal_data
    
    def set_personal(self, key: str, value: Any, category: str = "general"):
        """Set personal data"""
        self._personal_data[key] = {
            "value": value,
            "category": category,
            "updated_at": datetime.now().isoformat()
        }
        self._save_personal_data()
        self.episodic_db.store_personal(key, value, category)
    
    def delete_personal(self, key: str):
        """Delete personal data"""
        if key in self._personal_data:
            del self._personal_data[key]
            self._save_personal_data()
        self.episodic_db.delete_personal(key)
    
    def get_status(self) -> Dict[str, Any]:
        """Get memory agent status"""
        return {
            "agent_id": self.agent_id,
            "running": self._running,
            "capabilities": self.capabilities,
            "personal_entries": len(self._personal_data),
            "faiss_available": FAISS_AVAILABLE
        }


# Singleton instance
_memory_instance: Optional[MemoryAgent] = None


def get_memory(event_bus: Optional[EventBus] = None, memory_dir: str = "memory") -> MemoryAgent:
    """Get or create the memory agent singleton"""
    global _memory_instance
    if _memory_instance is None:
        _memory_instance = MemoryAgent(event_bus, memory_dir)
    return _memory_instance


if __name__ == "__main__":
    # Test the memory agent
    async def test_memory():
        bus = EventBus()
        await bus.start()
        
        memory = MemoryAgent(bus, memory_dir="test_memory")
        await memory.start()
        
        print("=" * 60)
        print("J.A.R.V.I.S. Memory Agent Test")
        print("=" * 60)
        
        # Store some memories
        print("\nStoring memories...")
        memory.store("User prefers coffee over tea", memory_type="personal", 
                    metadata={"key": "preference_beverage", "category": "preferences"})
        memory.store("The meeting is scheduled for 3pm tomorrow", memory_type="episodic",
                    metadata={"role": "user", "conversation_id": "conv1"})
        memory.store("Python is a programming language", memory_type="fact")
        
        # Get personal data
        print("\nPersonal Data:")
        print(memory.get_personal())
        
        # Search memories
        print("\nSearching for 'coffee'...")
        results = await memory.search("coffee")
        for r in results:
            print(f"  - [{r['type']}] {r['content'][:50]}...")
        
        # Get status
        print("\n" + "=" * 60)
        print("Memory Agent Status:")
        print(memory.get_status())
        
        await memory.stop()
        await bus.stop()
        
        # Cleanup
        import shutil
        if os.path.exists("test_memory"):
            shutil.rmtree("test_memory")
    
    asyncio.run(test_memory())
