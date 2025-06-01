"""Memory management for AI agents."""

from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Deque
import heapq
import uuid


class MemoryType(Enum):
    """Types of memory."""

    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    WORKING = "working"


@dataclass
class Memory:
    """A single memory item."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    content: Any = None
    type: MemoryType = MemoryType.SHORT_TERM
    importance: float = 0.5  # 0.0 to 1.0
    created: datetime = field(default_factory=datetime.utcnow)
    accessed: datetime = field(default_factory=datetime.utcnow)
    access_count: int = 0
    decay_rate: float = 0.1  # How fast the memory decays
    tags: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)

    def access(self) -> None:
        """Record memory access."""
        self.accessed = datetime.utcnow()
        self.access_count += 1

    def get_relevance(self, current_time: datetime | None = None) -> float:
        """Calculate current relevance based on importance and recency."""
        if current_time is None:
            current_time = datetime.utcnow()

        # Time decay
        time_elapsed = (current_time - self.accessed).total_seconds() / 3600  # hours
        time_decay = pow(0.5, time_elapsed * self.decay_rate)  # exponential decay

        # Access frequency boost
        frequency_boost = min(1.0, self.access_count / 10)

        # Combined relevance
        relevance = self.importance * time_decay * (1 + frequency_boost * 0.5)
        return max(0.0, min(1.0, relevance))

    def add_tag(self, tag: str) -> None:
        """Add a tag to the memory."""
        self.tags.add(tag)

    def has_tag(self, tag: str) -> bool:
        """Check if memory has a tag."""
        return tag in self.tags

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "content": self.content,
            "type": self.type.value,
            "importance": self.importance,
            "created": self.created.isoformat(),
            "accessed": self.accessed.isoformat(),
            "access_count": self.access_count,
            "decay_rate": self.decay_rate,
            "tags": list(self.tags),
            "metadata": self.metadata,
        }


class MemoryStore(ABC):
    """Abstract base class for memory stores."""

    @abstractmethod
    def store(self, memory: Memory) -> None:
        """Store a memory."""
        pass

    @abstractmethod
    def retrieve(self, memory_id: str) -> Memory | None:
        """Retrieve a specific memory."""
        pass

    @abstractmethod
    def search(self, query: str, limit: int = 10) -> list[Memory]:
        """Search memories."""
        pass

    @abstractmethod
    def forget(self, memory_id: str) -> None:
        """Remove a memory."""
        pass

    @abstractmethod
    def clear(self) -> None:
        """Clear all memories."""
        pass


class SimpleMemoryStore(MemoryStore):
    """Simple in-memory store."""

    def __init__(self, max_size: int = 1000):
        """Initialize store."""
        self.memories: dict[str, Memory] = {}
        self.max_size = max_size
        self._access_queue: Deque[str] = deque(maxlen=max_size)

    def store(self, memory: Memory) -> None:
        """Store a memory."""
        # Evict least recently used if at capacity
        if len(self.memories) >= self.max_size and memory.id not in self.memories:
            if self._access_queue:
                oldest_id = self._access_queue[0]
                if oldest_id in self.memories:
                    del self.memories[oldest_id]

        self.memories[memory.id] = memory
        self._access_queue.append(memory.id)

    def retrieve(self, memory_id: str) -> Memory | None:
        """Retrieve a specific memory."""
        memory = self.memories.get(memory_id)
        if memory:
            memory.access()
            # Move to end of access queue
            if memory_id in self._access_queue:
                self._access_queue.remove(memory_id)
            self._access_queue.append(memory_id)
        return memory

    def search(self, query: str, limit: int = 10) -> list[Memory]:
        """Search memories by content or tags."""
        query_lower = query.lower()
        results = []

        for memory in self.memories.values():
            # Search in content
            if (
                isinstance(memory.content, str)
                and query_lower in memory.content.lower()
            ):
                results.append((memory.get_relevance(), memory))
            # Search in tags
            elif any(query_lower in tag.lower() for tag in memory.tags):
                results.append((memory.get_relevance(), memory))

        # Sort by relevance and return top results
        results.sort(key=lambda x: x[0], reverse=True)
        return [memory for _, memory in results[:limit]]

    def forget(self, memory_id: str) -> None:
        """Remove a memory."""
        if memory_id in self.memories:
            del self.memories[memory_id]
            if memory_id in self._access_queue:
                self._access_queue.remove(memory_id)

    def clear(self) -> None:
        """Clear all memories."""
        self.memories.clear()
        self._access_queue.clear()


class WorkingMemory:
    """Working memory for current context."""

    def __init__(self, capacity: int = 7):  # Miller's magic number
        """Initialize working memory."""
        self.capacity = capacity
        self.items: list[tuple[float, Memory]] = []  # (priority, memory) heap
        self._id_to_priority: dict[str, float] = {}

    def add(self, memory: Memory, priority: float | None = None) -> None:
        """Add to working memory."""
        if priority is None:
            priority = memory.importance

        # If at capacity, remove lowest priority
        if len(self.items) >= self.capacity:
            if self.items and priority > self.items[0][0]:
                removed = heapq.heappop(self.items)
                del self._id_to_priority[removed[1].id]

        if len(self.items) < self.capacity:
            heapq.heappush(self.items, (priority, memory))
            self._id_to_priority[memory.id] = priority

    def get_all(self) -> list[Memory]:
        """Get all items in working memory."""
        return [
            memory for _, memory in sorted(self.items, key=lambda x: x[0], reverse=True)
        ]

    def contains(self, memory_id: str) -> bool:
        """Check if memory is in working memory."""
        return memory_id in self._id_to_priority

    def clear(self) -> None:
        """Clear working memory."""
        self.items.clear()
        self._id_to_priority.clear()

    def to_context(self) -> str:
        """Convert working memory to context string."""
        memories = self.get_all()
        if not memories:
            return ""

        lines = ["Current context:"]
        for i, memory in enumerate(memories, 1):
            if isinstance(memory.content, str):
                lines.append(f"{i}. {memory.content}")
            else:
                lines.append(f"{i}. {str(memory.content)}")

        return "\n".join(lines)


class MemoryManager:
    """Manages different types of memory."""

    def __init__(
        self,
        short_term_size: int = 100,
        long_term_size: int = 10000,
        working_capacity: int = 7,
    ):
        """Initialize memory manager."""
        self.short_term = SimpleMemoryStore(max_size=short_term_size)
        self.long_term = SimpleMemoryStore(max_size=long_term_size)
        self.working = WorkingMemory(capacity=working_capacity)
        self.episodic_memories: list[Memory] = []

    def remember(
        self,
        content: Any,
        importance: float = 0.5,
        memory_type: MemoryType = MemoryType.SHORT_TERM,
        tags: set[str] | None = None,
        **metadata,
    ) -> Memory:
        """Create and store a memory."""
        memory = Memory(
            content=content,
            type=memory_type,
            importance=importance,
            tags=tags or set(),
            metadata=metadata,
        )

        # Store in appropriate location
        if memory_type == MemoryType.SHORT_TERM:
            self.short_term.store(memory)
        elif memory_type == MemoryType.LONG_TERM:
            self.long_term.store(memory)
        elif memory_type == MemoryType.EPISODIC:
            self.episodic_memories.append(memory)
        elif memory_type == MemoryType.WORKING:
            self.working.add(memory)

        return memory

    def recall(self, memory_id: str) -> Memory | None:
        """Recall a specific memory."""
        # Check all stores
        memory = self.short_term.retrieve(memory_id)
        if memory:
            return memory

        memory = self.long_term.retrieve(memory_id)
        if memory:
            return memory

        # Check episodic
        for mem in self.episodic_memories:
            if mem.id == memory_id:
                mem.access()
                return mem

        return None

    def search(self, query: str, limit: int = 10) -> list[Memory]:
        """Search across all memory stores."""
        results = []

        # Search short-term
        results.extend(self.short_term.search(query, limit))

        # Search long-term
        results.extend(self.long_term.search(query, limit))

        # Search episodic
        query_lower = query.lower()
        for memory in self.episodic_memories:
            if (
                isinstance(memory.content, str)
                and query_lower in memory.content.lower()
            ):
                results.append(memory)
            elif any(query_lower in tag.lower() for tag in memory.tags):
                results.append(memory)

        # Sort by relevance and deduplicate
        seen = set()
        unique_results = []
        for memory in sorted(results, key=lambda m: m.get_relevance(), reverse=True):
            if memory.id not in seen:
                seen.add(memory.id)
                unique_results.append(memory)

        return unique_results[:limit]

    def consolidate(self, threshold: float = 0.7) -> int:
        """Move important short-term memories to long-term."""
        consolidated = 0

        for memory in list(self.short_term.memories.values()):
            if memory.importance >= threshold or memory.access_count > 5:
                # Move to long-term
                self.long_term.store(memory)
                self.short_term.forget(memory.id)
                memory.type = MemoryType.LONG_TERM
                consolidated += 1

        return consolidated

    def forget_irrelevant(self, relevance_threshold: float = 0.1) -> int:
        """Forget memories below relevance threshold."""
        forgotten = 0
        current_time = datetime.utcnow()

        # Check short-term memories
        for memory_id, memory in list(self.short_term.memories.items()):
            if memory.get_relevance(current_time) < relevance_threshold:
                self.short_term.forget(memory_id)
                forgotten += 1

        return forgotten

    def create_episode(self, description: str, memories: list[Memory]) -> Memory:
        """Create an episodic memory from multiple memories."""
        episode_content = {
            "description": description,
            "memories": [m.id for m in memories],
            "summary": "\n".join([str(m.content) for m in memories[:5]]),
        }

        episode = Memory(
            content=episode_content,
            type=MemoryType.EPISODIC,
            importance=max(m.importance for m in memories) if memories else 0.5,
            tags={"episode"},
        )

        self.episodic_memories.append(episode)
        return episode

    def get_context(self) -> dict[str, Any]:
        """Get current memory context."""
        return {
            "working_memory": self.working.to_context(),
            "short_term_count": len(self.short_term.memories),
            "long_term_count": len(self.long_term.memories),
            "episodic_count": len(self.episodic_memories),
            "recent_memories": [
                m.content
                for m in sorted(
                    self.short_term.memories.values(),
                    key=lambda m: m.accessed,
                    reverse=True,
                )[:5]
            ],
        }
