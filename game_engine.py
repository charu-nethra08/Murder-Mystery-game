"""
Murder Mystery - The Detective Challenge
=========================================
Backend engine. Same core DSA structures as before, now driving a full
multi-case game with suspect profiles, an action-based investigation system,
interrogation with contradiction detection, misleading/debunked clues,
an evidence board, and scoring.

  Concept                     Used for
  ---------------------------  --------------------------------------------
  Graph (adjacency list)       Suspect <-> victim relationship network
  BFS (shortest path)          "How is suspect X connected to victim?"
  Stack (LIFO)                 Investigation action log
  Queue (FIFO)                 "Call in next suspect" interrogation order
  Heap (priority queue)        Live suspicion ranking
  Binary Search Tree           Chronological clue timeline
  Hash Map (dict)              Evidence locker keyed by suspect
  Sorting                      Final leaderboard / score breakdown
"""

import heapq
import itertools
from collections import deque
from dataclasses import dataclass, field
from typing import Optional


# ============================================================================
# GENERIC DSA STRUCTURES (case-agnostic, reused by every case)
# ============================================================================
class RelationshipGraph:
    """Undirected graph. Nodes = people. Edges = relationships."""

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

    def relations_of(self, name: str) -> list[tuple[str, str]]:
        return self.adj.get(name, [])


class InvestigationStack:
    """LIFO stack: log of investigation actions performed, most recent last."""

    def __init__(self):
        self._items: list[str] = []

    def push(self, action: str):
        self._items.append(action)

    def peek(self) -> Optional[str]:
        return self._items[-1] if self._items else None

    def history(self) -> list[str]:
        return list(self._items)


class InterrogationQueue:
    """FIFO queue of suspects waiting to be called in for questioning."""

    def __init__(self):
        self._q: deque[str] = deque()

    def enqueue(self, suspect: str):
        if suspect not in self._q:
            self._q.append(suspect)

    def dequeue(self) -> Optional[str]:
        return self._q.popleft() if self._q else None

    def upcoming(self) -> list[str]:
        return list(self._q)


class SuspicionHeap:
    """Max-heap (via negated values) of (suspicion_score, suspect)."""

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
        self._heap = []
        self._counter = itertools.count()
        for suspect, score in scores.items():
            self.push(suspect, score)

    def ranked(self) -> list[tuple[str, int]]:
        return [(s, -neg) for neg, _, s in sorted(self._heap)]


@dataclass
class BSTNode:
    time: int
    clue: "Clue"
    left: Optional["BSTNode"] = None
    right: Optional["BSTNode"] = None


class TimelineBST:
    """BST keyed by clue timestamp. In-order traversal = chronological order."""

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


class EvidenceLocker:
    """Hash map: suspect name -> list of clues found against them."""

    def __init__(self):
        self._table: dict[str, list["Clue"]] = {}

    def add(self, suspect: str, clue: "Clue"):
        self._table.setdefault(suspect, []).append(clue)

    def get(self, suspect: str) -> list["Clue"]:
        return self._table.get(suspect, [])

    def all_suspects(self) -> list[str]:
        return list(self._table.keys())


# ============================================================================
# DOMAIN MODEL
# ============================================================================
@dataclass
class Suspect:
    name: str
    age: int
    relationship: str
    motive: str
    alibi: str
    personality: str
    avatar: str
    guilty: bool = False


ACTIONS = [
    ("search_room", "🔎 Search Room"),
    ("check_phone", "📱 Check Phone"),
    ("check_cctv", "🎥 Check CCTV"),
    ("read_messages", "📝 Read Messages"),
    ("examine_weapon", "🩸 Examine Weapon"),
    ("check_fingerprints", "👣 Check Fingerprints"),
]


@dataclass
class Clue:
    id: str
    description: str
    action: str            # one of ACTIONS keys
    points_to: str          # suspect name
    weight: int
    time: int                # minutes since midnight -> BST key
    critical: bool = False     # counts toward "important clue" score
    misleading: bool = False
    debunked_by: Optional[str] = None   # id of the clue that discredits this one


QUESTIONS = [
    ("q1", "Where were you at the time of the murder?"),
    ("q2", "Did you have any conflict with the victim?"),
    ("q3", "What do you know about the murder weapon?"),
    ("q4", "Were you in contact with the victim that day?"),
]


@dataclass
class SuspectAnswer:
    text: str
    contradicted_by: Optional[str] = None   # clue id that contradicts this answer


# ============================================================================
# CASE
# ============================================================================
class Case:
    def __init__(self, id, title, icon, description, victim, murderer,
                 correct_motive, correct_weapon, weapon_options, motive_options,
                 suspects: list[Suspect], relationships: list[tuple[str, str, str]],
                 clues: list[Clue], answers: dict[tuple[str, str], SuspectAnswer]):
        self.id = id
        self.title = title
        self.icon = icon
        self.description = description
        self.victim = victim
        self.murderer = murderer
        self.correct_motive = correct_motive
        self.correct_weapon = correct_weapon
        self.weapon_options = weapon_options
        self.motive_options = motive_options

        self.suspects: dict[str, Suspect] = {s.name: s for s in suspects}
        self.clues = clues
        self.clue_by_id = {c.id: c for c in clues}
        self.answers = answers

        self.graph = RelationshipGraph()
        self.graph.add_person(victim)
        for name in self.suspects:
            self.graph.add_person(name)
        for a, b, rel in relationships:
            self.graph.add_relationship(a, b, rel)

        self.stack = InvestigationStack()
        self.queue = InterrogationQueue()
        for name in self.suspects:
            self.queue.enqueue(name)
        self.heap = SuspicionHeap()
        self.timeline = TimelineBST()
        self.locker = EvidenceLocker()

        self.found_clue_ids: set[str] = set()
        self.debunked_ids: set[str] = set()
        self.actions_done: set[str] = set()
        self.interrogated_suspects: set[str] = set()
        self.asked_log: list[tuple[str, str]] = []   # (suspect, question_id)
        self.solved = False

    # ------------------------------------------------------------------
    def perform_action(self, action: str) -> Optional[Clue]:
        """Reveal the clue tied to this action (STACK logs the action)."""
        self.stack.push(action)
        self.actions_done.add(action)
        clue = next((c for c in self.clues if c.action == action), None)
        if clue is None or clue.id in self.found_clue_ids:
            return None
        self.found_clue_ids.add(clue.id)
        self.timeline.insert(clue)
        self.locker.add(clue.points_to, clue)
        self._apply_debunking()
        self._refresh_heap()
        return clue

    def _apply_debunking(self):
        for c in self.clues:
            if c.debunked_by and c.debunked_by in self.found_clue_ids:
                self.debunked_ids.add(c.id)

    def effective_weight(self, suspect: str) -> int:
        return sum(
            c.weight for c in self.locker.get(suspect)
            if c.id not in self.debunked_ids
        )

    def _refresh_heap(self):
        scores = {name: max(self.effective_weight(name), 0) for name in self.suspects}
        self.heap.rebuild(scores)

    # ------------------------------------------------------------------
    def interrogate_next(self) -> Optional[str]:
        nxt = self.queue.dequeue()
        if nxt:
            self.interrogated_suspects.add(nxt)
        return nxt

    def ask_question(self, suspect: str, question_id: str) -> tuple[SuspectAnswer, bool]:
        self.interrogated_suspects.add(suspect)
        self.asked_log.append((suspect, question_id))
        ans = self.answers[(suspect, question_id)]
        contradiction = bool(ans.contradicted_by) and ans.contradicted_by in self.found_clue_ids
        return ans, contradiction

    # ------------------------------------------------------------------
    def suspicion_ranking(self) -> list[tuple[str, int]]:
        return self.heap.ranked()

    def full_timeline(self) -> list[Clue]:
        return self.timeline.in_order()

    def critical_found_count(self) -> int:
        return sum(
            1 for c in self.clues
            if c.critical and c.id in self.found_clue_ids and c.id not in self.debunked_ids
        )

    def sorted_leaderboard(self) -> list[tuple[str, int]]:
        pairs = [(name, self.effective_weight(name)) for name in self.suspects]
        return sorted(pairs, key=lambda p: p[1], reverse=True)

    # ------------------------------------------------------------------
    def accuse(self, murderer: str, motive: str, weapon: str) -> dict:
        self.solved = True
        return {
            "murderer_correct": murderer == self.murderer,
            "motive_correct": motive == self.correct_motive,
            "weapon_correct": weapon == self.correct_weapon,
            "accused": murderer,
            "actual_murderer": self.murderer,
        }


# ============================================================================
# SCORING
# ============================================================================
def compute_score(case: Case, result: dict) -> tuple[int, dict]:
    clue_pts = min(case.critical_found_count(), 2) * 10       # up to 20
    murder_pts = 50 if result["murderer_correct"] else -30
    motive_pts = 20 if result["motive_correct"] else 0
    weapon_pts = 10 if result["weapon_correct"] else 0
    total = clue_pts + murder_pts + motive_pts + weapon_pts
    breakdown = {
        "Clues found": clue_pts,
        "Correct murderer": murder_pts,
        "Correct motive": motive_pts,
        "Correct weapon": weapon_pts,
    }
    return max(0, total), breakdown


# ============================================================================
# CASE DATA — 4 full cases
# ============================================================================
def _case_hostel() -> Case:
    suspects = [
        Suspect("Arjun Mehta", 20, "Roommate", "An unpaid debt of \u20b915,000 owed to the victim",
                 "I was in the library till midnight, studying for an exam.",
                 "Nervous, evasive", "🧑\u200d🎓", guilty=True),
        Suspect("Priya Nair", 19, "Girlfriend", "Believed the victim was cheating on her",
                 "I was in my room studying alone.", "Emotional, defensive", "👩\u200d🎓"),
        Suspect("Karan Singh", 21, "Senior student / rival", "Victim reported him for ragging juniors",
                 "I was at the gym, then went to return a library book.", "Aggressive, confident", "🏋️"),
        Suspect("Meena Iyer", 45, "Hostel warden", "Victim caught her taking bribes from students",
                 "I was doing my rounds on the other floor.", "Calm, calculating", "🧑\u200d💼"),
    ]
    relationships = [
        ("Rohan Verma", "Arjun Mehta", "roommate"),
        ("Rohan Verma", "Priya Nair", "girlfriend"),
        ("Rohan Verma", "Karan Singh", "reported for ragging"),
        ("Rohan Verma", "Meena Iyer", "warden"),
        ("Arjun Mehta", "Priya Nair", "friends"),
    ]
    clues = [
        Clue("h1", "A torn IOU note for \u20b915,000 found under Arjun's mattress, signed by the victim.",
             "search_room", "Arjun Mehta", 25, 20 * 60, critical=True),
        Clue("h2", "The victim's phone shows a heated argument thread with Arjun about the unpaid loan.",
             "check_phone", "Arjun Mehta", 20, 21 * 60 + 30, critical=True),
        Clue("h3", "CCTV shows Karan entering the hostel block at 10:45 PM, leaving at 10:50 PM.",
             "check_cctv", "Karan Singh", 22 * 60 + 45, 22 * 60 + 45, misleading=True, debunked_by="h4"),
        Clue("h4", "The librarian's late-checkout log confirms Karan only returned a borrowed book at that time.",
             "read_messages", "Karan Singh", 0, 22 * 60 + 50),
        Clue("h5", "The mess-hall kitchen knife has been wiped clean, but a faint blood smear remains near the handle.",
             "examine_weapon", "Arjun Mehta", 10, 23 * 60),
        Clue("h6", "A smudged partial fingerprint on the knife handle matches Arjun Mehta.",
             "check_fingerprints", "Arjun Mehta", 20, 23 * 60 + 5, critical=True),
    ]
    answers = {
        ("Arjun Mehta", "q1"): SuspectAnswer("I was in the library till midnight, studying for an exam.", contradicted_by="h2"),
        ("Arjun Mehta", "q2"): SuspectAnswer("No conflicts — we were just roommates."),
        ("Arjun Mehta", "q3"): SuspectAnswer("I don't know anything about a knife."),
        ("Arjun Mehta", "q4"): SuspectAnswer("We barely spoke that day."),
        ("Priya Nair", "q1"): SuspectAnswer("I was in my room studying alone."),
        ("Priya Nair", "q2"): SuspectAnswer("We had a small argument about his behavior, nothing serious."),
        ("Priya Nair", "q3"): SuspectAnswer("I've never even been near the mess hall kitchen."),
        ("Priya Nair", "q4"): SuspectAnswer("We texted a bit in the evening."),
        ("Karan Singh", "q1"): SuspectAnswer("I was at the gym, then returned a library book."),
        ("Karan Singh", "q2"): SuspectAnswer("He filed a ragging complaint against me. I was angry, but I moved on."),
        ("Karan Singh", "q3"): SuspectAnswer("No idea about any weapon."),
        ("Karan Singh", "q4"): SuspectAnswer("No contact that day."),
        ("Meena Iyer", "q1"): SuspectAnswer("I was doing my rounds on the other floor."),
        ("Meena Iyer", "q2"): SuspectAnswer("He caught me taking money from students. I handled it quietly."),
        ("Meena Iyer", "q3"): SuspectAnswer("The kitchen knives are common property — anyone could take one."),
        ("Meena Iyer", "q4"): SuspectAnswer("I saw him briefly during dinner."),
    }
    return Case(
        id="hostel", title="Case 1 — Murder at the Hostel", icon="🏠",
        description="Rohan Verma, a final-year student, was found dead in his hostel room at 11 PM.",
        victim="Rohan Verma", murderer="Arjun Mehta",
        correct_motive="An unpaid debt of \u20b915,000 owed to the victim",
        correct_weapon="Kitchen knife",
        weapon_options=["Kitchen knife", "Cricket bat", "Scissors", "Rope"],
        motive_options=[
            "An unpaid debt of \u20b915,000 owed to the victim",
            "Believed the victim was cheating on her",
            "Victim reported him for ragging juniors",
            "Victim caught her taking bribes from students",
        ],
        suspects=suspects, relationships=relationships, clues=clues, answers=answers,
    )


def _case_hotel() -> Case:
    suspects = [
        Suspect("Neha Kapoor", 24, "Hotel receptionist", "Victim repeatedly harassed her at the front desk",
                 "I was at the front desk all evening, cameras can confirm.", "Anxious", "💁\u200d♀️"),
        Suspect("Rakesh Malhotra", 50, "Business rival", "Victim was about to expose his financial fraud",
                 "I was in my room all night, room service can confirm.", "Smug, calculating", "🕴️", guilty=True),
        Suspect("Sana Sheikh", 29, "Victim's secretary", "Victim was planning to fire her",
                 "I was in the hotel gym around that time.", "Nervous", "👩\u200d💼"),
        Suspect("Deepak Rao", 35, "Room service waiter", "Victim insulted him and refused to tip",
                 "I was serving other rooms on that floor.", "Quiet, observant", "🧑\u200d🍳"),
    ]
    relationships = [
        ("Vikram Oberoi", "Neha Kapoor", "hotel guest"),
        ("Vikram Oberoi", "Rakesh Malhotra", "business rival"),
        ("Vikram Oberoi", "Sana Sheikh", "employer"),
        ("Vikram Oberoi", "Deepak Rao", "guest of hotel"),
        ("Rakesh Malhotra", "Sana Sheikh", "knew each other"),
    ]
    clues = [
        Clue("o1", "An empty poison vial hidden in the minibar, wrapped in a napkin marked 'R.M.'",
             "search_room", "Rakesh Malhotra", 25, 20 * 60, critical=True),
        Clue("o2", "CCTV shows Rakesh leaving his room at 8:50 PM and returning at 9:25 PM — contradicting his claim he never left.",
             "check_cctv", "Rakesh Malhotra", 20, 21 * 60, critical=True),
        Clue("o3", "The victim's phone log shows a 12-minute call with Deepak at 8:40 PM about a room-service complaint.",
             "check_phone", "Deepak Rao", 10, 20 * 60 + 40, misleading=True, debunked_by="o4"),
        Clue("o4", "Hotel logs confirm the call was Deepak apologizing for a wrong delivery — unrelated to the murder.",
             "read_messages", "Deepak Rao", 0, 20 * 60 + 45),
        Clue("o5", "The wine glass shows trace residue of a rare poison also found in Rakesh's briefcase.",
             "examine_weapon", "Rakesh Malhotra", 20, 21 * 60 + 15, critical=True),
        Clue("o6", "A partial fingerprint on the minibar matches Rakesh Malhotra.",
             "check_fingerprints", "Rakesh Malhotra", 15, 21 * 60 + 20),
    ]
    answers = {
        ("Neha Kapoor", "q1"): SuspectAnswer("I was at the front desk all evening, cameras can confirm."),
        ("Neha Kapoor", "q2"): SuspectAnswer("He made me uncomfortable a few times, but nothing worth this."),
        ("Neha Kapoor", "q3"): SuspectAnswer("I don't know anything about poison."),
        ("Neha Kapoor", "q4"): SuspectAnswer("He called down asking for extra towels once."),
        ("Rakesh Malhotra", "q1"): SuspectAnswer("I was in my room all night, room service can confirm.", contradicted_by="o2"),
        ("Rakesh Malhotra", "q2"): SuspectAnswer("We had business disagreements — nothing personal."),
        ("Rakesh Malhotra", "q3"): SuspectAnswer("I have no idea what killed him."),
        ("Rakesh Malhotra", "q4"): SuspectAnswer("We spoke briefly about a contract."),
        ("Sana Sheikh", "q1"): SuspectAnswer("I was in the hotel gym around that time."),
        ("Sana Sheikh", "q2"): SuspectAnswer("He was planning to let me go. I was upset, not violent."),
        ("Sana Sheikh", "q3"): SuspectAnswer("I've never touched poison in my life."),
        ("Sana Sheikh", "q4"): SuspectAnswer("I texted him about tomorrow's meeting."),
        ("Deepak Rao", "q1"): SuspectAnswer("I was serving other rooms on that floor."),
        ("Deepak Rao", "q2"): SuspectAnswer("He never tipped and was rude, but that's normal for guests."),
        ("Deepak Rao", "q3"): SuspectAnswer("I only handle food, not weapons."),
        ("Deepak Rao", "q4"): SuspectAnswer("I delivered a wrong order to his floor by mistake."),
    }
    return Case(
        id="hotel", title="Case 2 — Murder at the Hotel", icon="🏨",
        description="Vikram Oberoi, a businessman, was found dead in his hotel suite at 10 PM.",
        victim="Vikram Oberoi", murderer="Rakesh Malhotra",
        correct_motive="Victim was about to expose his financial fraud",
        correct_weapon="Poisoned wine",
        weapon_options=["Poisoned wine", "Letter opener", "Pillow suffocation", "Electric wire"],
        motive_options=[
            "Victim was about to expose his financial fraud",
            "Victim repeatedly harassed her at the front desk",
            "Victim was planning to fire her",
            "Victim insulted him and refused to tip",
        ],
        suspects=suspects, relationships=relationships, clues=clues, answers=answers,
    )


def _case_office() -> Case:
    suspects = [
        Suspect("Rohit Bansal", 48, "CEO", "She found evidence he was embezzling company funds",
                 "I left the office at 6 PM for a client dinner.", "Charming, controlling", "🧑\u200d💼", guilty=True),
        Suspect("Anjali Desai", 38, "HR Manager", "She was about to expose Anjali's fake degree",
                 "I was working late in HR, alone.", "Defensive", "👩\u200d💻"),
        Suspect("Suresh Iyer", 30, "IT Admin", "She caught him leaking company data",
                 "I was fixing a server issue till 9 PM, the team can confirm.", "Awkward, tech-focused", "🧑\u200d🔧"),
        Suspect("Divya Kulkarni", 26, "Junior Accountant", "She unfairly blamed Divya for a financial discrepancy",
                 "I left at 5:30 PM, before anything happened.", "Quiet, resentful", "👩\u200d💼"),
    ]
    relationships = [
        ("Kavita Sharma", "Rohit Bansal", "CEO / CFO"),
        ("Kavita Sharma", "Anjali Desai", "colleagues"),
        ("Kavita Sharma", "Suresh Iyer", "colleagues"),
        ("Kavita Sharma", "Divya Kulkarni", "supervised her"),
        ("Rohit Bansal", "Anjali Desai", "colleagues"),
    ]
    clues = [
        Clue("f1", "A shredded financial report found in Rohit's trash, matching the one Kavita was investigating.",
             "search_room", "Rohit Bansal", 25, 19 * 60, critical=True),
        Clue("f2", "CCTV shows Rohit re-entering the building at 7:45 PM despite claiming he left at 6 PM.",
             "check_cctv", "Rohit Bansal", 20, 19 * 60 + 45, critical=True),
        Clue("f3", "The victim's phone shows an angry email draft to Suresh about a data leak, sent at 7 PM.",
             "check_phone", "Suresh Iyer", 10, 19 * 60, misleading=True, debunked_by="f4"),
        Clue("f4", "IT server logs confirm Suresh was on a support call from 6:30 to 9 PM, unable to leave his desk.",
             "read_messages", "Suresh Iyer", 0, 19 * 60 + 10),
        Clue("f5", "The brass paperweight has been wiped, but a smear of hand sanitizer matches the brand used only in the executive suite.",
             "examine_weapon", "Rohit Bansal", 15, 20 * 60, critical=True),
        Clue("f6", "A partial fingerprint on the paperweight's edge matches Rohit Bansal.",
             "check_fingerprints", "Rohit Bansal", 20, 20 * 60 + 5),
    ]
    answers = {
        ("Rohit Bansal", "q1"): SuspectAnswer("I left the office at 6 PM for a client dinner.", contradicted_by="f2"),
        ("Rohit Bansal", "q2"): SuspectAnswer("We disagreed on budget decisions sometimes — that's normal."),
        ("Rohit Bansal", "q3"): SuspectAnswer("I don't even know what was used."),
        ("Rohit Bansal", "q4"): SuspectAnswer("We spoke briefly about the quarterly report."),
        ("Anjali Desai", "q1"): SuspectAnswer("I was working late in HR, alone."),
        ("Anjali Desai", "q2"): SuspectAnswer("She was strict, but professional."),
        ("Anjali Desai", "q3"): SuspectAnswer("I have no idea about any weapon."),
        ("Anjali Desai", "q4"): SuspectAnswer("No contact that evening."),
        ("Suresh Iyer", "q1"): SuspectAnswer("I was fixing a server issue till 9 PM, the team can confirm."),
        ("Suresh Iyer", "q2"): SuspectAnswer("She confronted me about a data leak. I denied it."),
        ("Suresh Iyer", "q3"): SuspectAnswer("I only deal with computers, not office objects."),
        ("Suresh Iyer", "q4"): SuspectAnswer("She emailed me angrily earlier that day."),
        ("Divya Kulkarni", "q1"): SuspectAnswer("I left at 5:30 PM, before anything happened."),
        ("Divya Kulkarni", "q2"): SuspectAnswer("She blamed me unfairly for a mistake that wasn't mine."),
        ("Divya Kulkarni", "q3"): SuspectAnswer("I've never been in her office after hours."),
        ("Divya Kulkarni", "q4"): SuspectAnswer("No contact after I left."),
    }
    return Case(
        id="office", title="Case 3 — Murder at the Office", icon="🏢",
        description="Kavita Sharma, the company CFO, was found dead in her office at 8 PM, after hours.",
        victim="Kavita Sharma", murderer="Rohit Bansal",
        correct_motive="She found evidence he was embezzling company funds",
        correct_weapon="Heavy brass paperweight",
        weapon_options=["Heavy brass paperweight", "Letter opener", "Scissors", "Broken glass"],
        motive_options=[
            "She found evidence he was embezzling company funds",
            "She was about to expose Anjali's fake degree",
            "She caught him leaking company data",
            "She unfairly blamed Divya for a financial discrepancy",
        ],
        suspects=suspects, relationships=relationships, clues=clues, answers=answers,
    )


def _case_mansion() -> Case:
    suspects = [
        Suspect("Lady Cordelia Grey", 52, "Wife", "A prenup dispute — she wanted out, with a share of the inheritance",
                 "I was in the drawing room reading.", "Composed, icy", "👩\u200d🦳"),
        Suspect("Nathaniel Grey", 29, "Estranged son", "The victim had just cut him out of the will entirely",
                 "I was in the guest wing, I arrived at the mansion late.", "Bitter, impulsive", "🤵", guilty=True),
        Suspect("Mrs. Higgins", 60, "Housekeeper", "The victim planned to fire her after 30 years of service",
                 "I was preparing the dining room for the next morning.", "Loyal but resentful", "👵"),
        Suspect("Dr. Simon Wells", 45, "Family lawyer", "The victim discovered he'd been embezzling trust funds",
                 "I was in the library reviewing documents.", "Smooth, evasive", "🧑\u200d⚖️"),
    ]
    relationships = [
        ("Lord Alistair Grey", "Lady Cordelia Grey", "spouse"),
        ("Lord Alistair Grey", "Nathaniel Grey", "father"),
        ("Lord Alistair Grey", "Mrs. Higgins", "employer"),
        ("Lord Alistair Grey", "Dr. Simon Wells", "client"),
        ("Dr. Simon Wells", "Lady Cordelia Grey", "handled her prenup"),
    ]
    clues = [
        Clue("m1", "A torn will draft found in Nathaniel's room, showing he'd be disinherited entirely.",
             "search_room", "Nathaniel Grey", 25, 18 * 60, critical=True),
        Clue("m2", "Security footage shows Nathaniel entering the study at 8:50 PM through the side door, not the guest wing as claimed.",
             "check_cctv", "Nathaniel Grey", 20, 20 * 60 + 50, critical=True),
        Clue("m3", "The victim's phone shows a panicked voicemail from Dr. Wells about 'the missing funds', left at 8:30 PM.",
             "check_phone", "Dr. Simon Wells", 10, 20 * 60 + 30, misleading=True, debunked_by="m4"),
        Clue("m4", "Dr. Wells's assistant confirms he was on a bank conference call from 8:00 to 9:15 PM, verified by call records.",
             "read_messages", "Dr. Simon Wells", 0, 20 * 60 + 35),
        Clue("m5", "The antique revolver's grip has been wiped, but gunpowder residue is found on a glove in Nathaniel's coat pocket.",
             "examine_weapon", "Nathaniel Grey", 20, 21 * 60, critical=True),
        Clue("m6", "A partial fingerprint on the revolver's chamber matches Nathaniel Grey.",
             "check_fingerprints", "Nathaniel Grey", 15, 21 * 60 + 5),
    ]
    answers = {
        ("Lady Cordelia Grey", "q1"): SuspectAnswer("I was in the drawing room reading, alone."),
        ("Lady Cordelia Grey", "q2"): SuspectAnswer("We'd grown distant, but I never wished him dead."),
        ("Lady Cordelia Grey", "q3"): SuspectAnswer("I don't know guns."),
        ("Lady Cordelia Grey", "q4"): SuspectAnswer("We didn't speak much that evening."),
        ("Nathaniel Grey", "q1"): SuspectAnswer("I was in the guest wing, I arrived at the mansion late.", contradicted_by="m2"),
        ("Nathaniel Grey", "q2"): SuspectAnswer("He cut me off financially. I was furious, but I didn't kill him."),
        ("Nathaniel Grey", "q3"): SuspectAnswer("That revolver's been in a display case for years."),
        ("Nathaniel Grey", "q4"): SuspectAnswer("We hadn't spoken in weeks."),
        ("Mrs. Higgins", "q1"): SuspectAnswer("I was preparing the dining room for the next morning."),
        ("Mrs. Higgins", "q2"): SuspectAnswer("He said he'd let me go after decades of service. It hurt."),
        ("Mrs. Higgins", "q3"): SuspectAnswer("I dust that display case every week, so my prints would be there anyway."),
        ("Mrs. Higgins", "q4"): SuspectAnswer("I brought him tea earlier that evening."),
        ("Dr. Simon Wells", "q1"): SuspectAnswer("I was in the library reviewing documents."),
        ("Dr. Simon Wells", "q2"): SuspectAnswer("We had a professional disagreement about the trust."),
        ("Dr. Simon Wells", "q3"): SuspectAnswer("Firearms aren't my area of expertise."),
        ("Dr. Simon Wells", "q4"): SuspectAnswer("I left him a voicemail about a banking matter."),
    }
    return Case(
        id="mansion", title="Case 4 — Murder at the Mansion", icon="🏰",
        description="Lord Alistair Grey, the wealthy patriarch, was found dead in his study at 9 PM.",
        victim="Lord Alistair Grey", murderer="Nathaniel Grey",
        correct_motive="The victim had just cut him out of the will entirely",
        correct_weapon="Antique revolver",
        weapon_options=["Antique revolver", "Fireplace poker", "Letter opener", "Poison"],
        motive_options=[
            "The victim had just cut him out of the will entirely",
            "A prenup dispute — she wanted out, with a share of the inheritance",
            "The victim planned to fire her after 30 years of service",
            "The victim discovered he'd been embezzling trust funds",
        ],
        suspects=suspects, relationships=relationships, clues=clues, answers=answers,
    )


CASE_FACTORIES = {
    "hostel": _case_hostel,
    "hotel": _case_hotel,
    "office": _case_office,
    "mansion": _case_mansion,
}


# ============================================================================
# TOP-LEVEL GAME CONTROLLER
# ============================================================================
class MysteryGame:
    def __init__(self):
        # one instance per case, used for home-screen listing (title/icon/desc)
        self.cases: dict[str, Case] = {cid: factory() for cid, factory in CASE_FACTORIES.items()}
        self.difficulty: str = "Medium"
        self.current_case_id: Optional[str] = None

    def start(self, case_id: str, difficulty: str):
        """Fresh instance of the chosen case so replays start clean."""
        self.cases[case_id] = CASE_FACTORIES[case_id]()
        self.current_case_id = case_id
        self.difficulty = difficulty

    @property
    def case(self) -> Case:
        return self.cases[self.current_case_id]
