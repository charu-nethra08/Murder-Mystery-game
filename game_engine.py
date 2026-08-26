"""
Murder Mystery Game — Backend Engine
=====================================
Every core mechanic is backed by a real data structure / algorithm:

  Concept                     Used for
  ---------------------------  --------------------------------------------
  Graph (adjacency list)       Suspect relationship network
  BFS (shortest path)          "How is suspect X connected to victim?"
  DFS (bounded)                "Who did suspect X interact with (2 hops)?"
  Stack (LIFO)                 Investigation history / "go back" button
  Queue (FIFO)                 Interrogation order
  Min/Max Heap (heapq)         Live suspicion ranking (priority queue)
  Binary Search Tree           Chronological clue timeline
  Hash Map (dict)              Evidence locker keyed by suspect
  Sorting (sorted())           Final leaderboard of suspects by evidence weight
"""

import heapq
import itertools
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


# ============================================================================
# 1. GRAPH — suspect relationship network
# ============================================================================
class RelationshipGraph:
    """Undirected weighted graph. Nodes = people. Edges = relationships."""

    def __init__(self):
        self.adj: dict[str, list[tuple[str, str]]] = {}

    def add_person(self, name: str):
        self.adj.setdefault(name, [])

    def add_relationship(self, a: str, b: str, relation: str):
        self.add_person(a)
        self.add_person(b)
        self.adj[a].append((b, relation))
        self.adj[b].append((a, relation))

    def bfs_path(self, start: str, end: str) -> Optional[list[str]]:
        """Shortest connection path between two people. Classic BFS."""
        if start not in self.adj or end not in self.adj:
            return None
        if start == end:
            return [start]
        visited = {start}
        queue = deque([[start]])
        while queue:
            path = queue.popleft()
            node = path[-1]
            for neighbor, _ in self.adj[node]:
                if neighbor in visited:
                    continue
                new_path = path + [neighbor]
                if neighbor == end:
                    return new_path
                visited.add(neighbor)
                queue.append(new_path)
        return None

    def dfs_connections(self, start: str, depth: int = 2) -> list[tuple[str, str, int]]:
        """All people reachable within `depth` hops of `start`. Recursive DFS."""
        visited = {start}
        result = []

        def dfs(node, d, hop):
            if d < 0:
                return
            for neighbor, relation in self.adj.get(node, []):
                if neighbor not in visited:
                    visited.add(neighbor)
                    result.append((neighbor, relation, hop))
                    dfs(neighbor, d - 1, hop + 1)

        dfs(start, depth, 1)
        return result

    def relations_of(self, name: str) -> list[tuple[str, str]]:
        return self.adj.get(name, [])


# ============================================================================
# 2. STACK — investigation history (undo / go back)
# ============================================================================
class InvestigationStack:
    """LIFO stack of visited locations, so the player can step back."""

    def __init__(self):
        self._items: list[str] = []

    def push(self, location: str):
        self._items.append(location)

    def pop(self) -> Optional[str]:
        return self._items.pop() if self._items else None

    def peek(self) -> Optional[str]:
        return self._items[-1] if self._items else None

    def history(self) -> list[str]:
        return list(self._items)

    def is_empty(self) -> bool:
        return not self._items


# ============================================================================
# 3. QUEUE — interrogation order
# ============================================================================
class InterrogationQueue:
    """FIFO queue: suspects wait their turn to be interrogated."""

    def __init__(self):
        self._q: deque[str] = deque()

    def enqueue(self, suspect: str):
        if suspect not in self._q:
            self._q.append(suspect)

    def dequeue(self) -> Optional[str]:
        return self._q.popleft() if self._q else None

    def upcoming(self) -> list[str]:
        return list(self._q)

    def is_empty(self) -> bool:
        return not self._q


# ============================================================================
# 4. HEAP — live suspicion ranking (priority queue)
# ============================================================================
class SuspicionHeap:
    """
    Max-heap (via negated values) of (suspicion_score, suspect).
    heapq is a binary min-heap internally; we store -score to simulate max-heap.
    A counter breaks ties so heap comparisons never fall back to comparing names.
    """

    def __init__(self):
        self._heap = []
        self._counter = itertools.count()

    def push(self, suspect: str, score: int):
        heapq.heappush(self._heap, (-score, next(self._counter), suspect))

    def top(self) -> Optional[tuple[str, int]]:
        if not self._heap:
            return None
        neg_score, _, suspect = self._heap[0]
        return suspect, -neg_score

    def rebuild(self, scores: dict[str, int]):
        """Rebuild the heap fresh from a suspect -> score mapping."""
        self._heap = []
        self._counter = itertools.count()
        for suspect, score in scores.items():
            self.push(suspect, score)

    def ranked(self) -> list[tuple[str, int]]:
        """Return all suspects sorted by suspicion, without mutating the heap."""
        return [(s, -neg) for neg, _, s in sorted(self._heap)]


# ============================================================================
# 5. BINARY SEARCH TREE — chronological clue timeline
# ============================================================================
@dataclass
class BSTNode:
    time: int
    clue: "Clue"
    left: Optional["BSTNode"] = None
    right: Optional["BSTNode"] = None


class TimelineBST:
    """BST keyed by clue timestamp (minutes since midnight). In-order
    traversal yields clues in perfect chronological order in O(n)."""

    def __init__(self):
        self.root: Optional[BSTNode] = None

    def insert(self, clue: "Clue"):
        self.root = self._insert(self.root, clue)

    def _insert(self, node, clue):
        if node is None:
            return BSTNode(clue.time, clue)
        if clue.time < node.time:
            node.left = self._insert(node.left, clue)
        else:
            node.right = self._insert(node.right, clue)
        return node

    def in_order(self) -> list["Clue"]:
        result = []

        def visit(node):
            if node is None:
                return
            visit(node.left)
            result.append(node.clue)
            visit(node.right)

        visit(self.root)
        return result

    def range_query(self, start: int, end: int) -> list["Clue"]:
        """All clues discovered between two timestamps — classic BST range search."""
        result = []

        def visit(node):
            if node is None:
                return
            if start < node.time:
                visit(node.left)
            if start <= node.time <= end:
                result.append(node.clue)
            if node.time < end:
                visit(node.right)

        visit(self.root)
        return result


# ============================================================================
# 6. HASH MAP — evidence locker
# ============================================================================
class EvidenceLocker:
    """Dict-backed hash map: suspect name -> list of evidence (O(1) lookup)."""

    def __init__(self):
        self._table: dict[str, list["Clue"]] = {}

    def add(self, suspect: str, clue: "Clue"):
        self._table.setdefault(suspect, []).append(clue)

    def get(self, suspect: str) -> list["Clue"]:
        return self._table.get(suspect, [])

    def weight_of(self, suspect: str) -> int:
        return sum(c.weight for c in self.get(suspect))

    def all_suspects(self) -> list[str]:
        return list(self._table.keys())


# ============================================================================
# Domain data
# ============================================================================
@dataclass
class Clue:
    id: str
    description: str
    location: str
    time: int              # minutes since midnight, used as BST key
    points_to: str          # suspect name
    weight: int              # suspicion contribution


@dataclass
class Suspect:
    name: str
    role: str
    motive: str
    alibi: str
    guilty: bool = False


# ============================================================================
# GAME ENGINE — ties every structure together
# ============================================================================
class GameEngine:
    def __init__(self):
        self.graph = RelationshipGraph()
        self.history = InvestigationStack()
        self.queue = InterrogationQueue()
        self.heap = SuspicionHeap()
        self.timeline = TimelineBST()
        self.locker = EvidenceLocker()

        self.victim = "Edmund Blackwood"
        self.suspects: dict[str, Suspect] = {}
        self.locations: dict[str, list[Clue]] = {}
        self.found_clue_ids: set[str] = set()
        self.solved = False

        self._build_case()

    # ------------------------------------------------------------------
    def _build_case(self):
        # --- Suspects -----------------------------------------------------
        suspects = [
            Suspect("Eleanor Blackwood", "Wife", "Inheritance of the estate", "Says she was asleep in her bedroom"),
            Suspect("James Carter", "Business Partner", "A crippling financial dispute", "Claims he left the estate at 8:30 PM"),
            Suspect("Sophia Reyes", "Housemaid", "Being blackmailed by the victim", "Says she was in the kitchen all evening"),
            Suspect("Marcus Whitfield", "Brother", "A decades-old inheritance rivalry", "Claims he was in the garden smoking"),
            Suspect("Dr. Victor Lang", "Family Doctor", "A secret affair the victim discovered", "Says he was reviewing files in the study", guilty=True),
        ]
        for s in suspects:
            self.suspects[s.name] = s
            self.graph.add_person(s.name)
            self.queue.enqueue(s.name)
        self.graph.add_person(self.victim)

        # --- Relationships (graph edges) -----------------------------------
        self.graph.add_relationship(self.victim, "Eleanor Blackwood", "spouse")
        self.graph.add_relationship(self.victim, "James Carter", "business partner")
        self.graph.add_relationship(self.victim, "Sophia Reyes", "employer")
        self.graph.add_relationship(self.victim, "Marcus Whitfield", "sibling")
        self.graph.add_relationship(self.victim, "Dr. Victor Lang", "patient")
        self.graph.add_relationship("Eleanor Blackwood", "Dr. Victor Lang", "secret affair")
        self.graph.add_relationship("James Carter", "Marcus Whitfield", "poker buddies")
        self.graph.add_relationship("Sophia Reyes", "James Carter", "overheard argument")

        # --- Locations & Clues (inserted into BST + hashmap) ---------------
        clues = [
            Clue("c1", "Wine glass with lipstick, only half-drunk, left in the library.", "Library", 20 * 60 + 45, "Eleanor Blackwood", 10),
            Clue("c2", "Torn business contract with James Carter's signature, dated today.", "Study", 19 * 60 + 10, "James Carter", 20),
            Clue("c3", "A muddy footprint leading from the garden to the library window.", "Garden", 20 * 60 + 30, "Marcus Whitfield", 15),
            Clue("c4", "A love letter signed 'V.L.' hidden in Eleanor's dresser.", "Bedroom", 18 * 60 + 0, "Dr. Victor Lang", 25),
            Clue("c5", "Kitchen logbook shows Sophia clocked out at 8:15, before the murder.", "Kitchen", 20 * 60 + 15, "Sophia Reyes", -10),
            Clue("c6", "A prescription bottle for a sedative, prescribed by Dr. Lang, found empty near the body.", "Library", 20 * 60 + 50, "Dr. Victor Lang", 30),
            Clue("c7", "Study desk drawer forced open; missing files on the victim's will.", "Study", 19 * 60 + 40, "James Carter", 10),
            Clue("c8", "Cigarette butts matching Marcus's brand, but stale — from days earlier.", "Garden", 17 * 60 + 0, "Marcus Whitfield", -5),
            Clue("c9", "Dr. Lang's medical bag found unlocked in the library, syringe missing.", "Library", 20 * 60 + 55, "Dr. Victor Lang", 20),
            Clue("c10", "Eleanor's alibi confirmed by a security camera timestamp at 9:00 PM.", "Bedroom", 21 * 60 + 0, "Eleanor Blackwood", -15),
        ]
        for clue in clues:
            self.locations.setdefault(clue.location, []).append(clue)

        # Room list (even empty ones, for navigation)
        for room in ["Library", "Kitchen", "Study", "Garden", "Bedroom", "Dining Room"]:
            self.locations.setdefault(room, [])

    # ------------------------------------------------------------------
    # Navigation (Stack)
    # ------------------------------------------------------------------
    def visit_location(self, location: str) -> list[Clue]:
        self.history.push(location)
        return self.locations.get(location, [])

    def go_back(self) -> Optional[str]:
        self.history.pop()  # discard current
        return self.history.peek()

    # ------------------------------------------------------------------
    # Clue discovery -> Hash Map + BST
    # ------------------------------------------------------------------
    def collect_clue(self, clue: Clue):
        if clue.id in self.found_clue_ids:
            return
        self.found_clue_ids.add(clue.id)
        self.timeline.insert(clue)
        self.locker.add(clue.points_to, clue)
        self._refresh_heap()

    def _refresh_heap(self):
        scores = {name: max(self.locker.weight_of(name), 0) for name in self.suspects}
        self.heap.rebuild(scores)

    # ------------------------------------------------------------------
    # Interrogation (Queue)
    # ------------------------------------------------------------------
    def interrogate_next(self) -> Optional[str]:
        return self.queue.dequeue()

    # ------------------------------------------------------------------
    # Rankings & timeline
    # ------------------------------------------------------------------
    def suspicion_ranking(self) -> list[tuple[str, int]]:
        return self.heap.ranked()

    def full_timeline(self) -> list[Clue]:
        return self.timeline.in_order()

    def timeline_between(self, start_hhmm: int, end_hhmm: int) -> list[Clue]:
        return self.timeline.range_query(start_hhmm, end_hhmm)

    def sorted_leaderboard(self) -> list[tuple[str, int]]:
        """Plain sort() over evidence weights — demonstrates classic sorting
        as distinct from the heap-based live ranking above."""
        pairs = [(name, self.locker.weight_of(name)) for name in self.suspects]
        return sorted(pairs, key=lambda p: p[1], reverse=True)

    # ------------------------------------------------------------------
    # Final accusation
    # ------------------------------------------------------------------
    def accuse(self, suspect_name: str) -> tuple[bool, str]:
        self.solved = True
        suspect = self.suspects[suspect_name]
        path = self.graph.bfs_path(suspect_name, self.victim)
        path_str = " → ".join(path) if path else "no known connection"
        if suspect.guilty:
            return True, f"Correct! {suspect_name} is the murderer. Connection to victim: {path_str}."
        return False, f"Incorrect. {suspect_name}'s connection to the victim was: {path_str}. Keep investigating."
