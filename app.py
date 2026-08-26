"""
Murder Mystery: The Blackwood Case
Streamlit frontend for game_engine.py

Run locally:
    streamlit run app.py
"""

import streamlit as st
from game_engine import GameEngine

st.set_page_config(page_title="The Blackwood Case", page_icon="🔎", layout="wide")

# ---------------------------------------------------------------------------
# Session state: keep ONE GameEngine instance alive across reruns
# ---------------------------------------------------------------------------
if "engine" not in st.session_state:
    st.session_state.engine = GameEngine()
if "current_location" not in st.session_state:
    st.session_state.current_location = None
if "interrogated" not in st.session_state:
    st.session_state.interrogated = []

engine: GameEngine = st.session_state.engine

st.title("🔎 The Blackwood Case")
st.caption("A murder mystery — every mechanic below is powered by a real data structure.")

# ---------------------------------------------------------------------------
# Sidebar navigation
# ---------------------------------------------------------------------------
page = st.sidebar.radio(
    "Investigation Menu",
    [
        "Case Overview",
        "Explore Locations (Stack)",
        "Relationship Web (Graph)",
        "Interrogation Queue",
        "Evidence Locker (Hash Map)",
        "Timeline (BST)",
        "Suspicion Ranking (Heap)",
        "Make an Accusation",
    ],
)

st.sidebar.markdown("---")
st.sidebar.metric("Clues found", f"{len(engine.found_clue_ids)} / 10")

# ===========================================================================
# CASE OVERVIEW
# ===========================================================================
if page == "Case Overview":
    st.header("The Case")
    st.write(
        f"**Victim:** {engine.victim}, found dead in the Library at 9:00 PM.\n\n"
        "Five people had motive, opportunity, or both. Explore the estate, "
        "gather evidence, interrogate suspects, and when you're ready, "
        "make your accusation."
    )
    cols = st.columns(len(engine.suspects))
    for col, (name, s) in zip(cols, engine.suspects.items()):
        with col:
            st.subheader(name)
            st.write(f"**Role:** {s.role}")
            st.write(f"**Motive:** {s.motive}")
            st.write(f"**Alibi:** {s.alibi}")

# ===========================================================================
# EXPLORE LOCATIONS — STACK
# ===========================================================================
elif page == "Explore Locations (Stack)":
    st.header("Explore the Estate")
    st.caption("Your visited rooms are tracked on a **stack** — 'Go Back' pops the last one.")

    rooms = list(engine.locations.keys())
    chosen = st.selectbox("Go to a room:", rooms)

    c1, c2 = st.columns([1, 1])
    if c1.button("Enter room"):
        st.session_state.current_location = chosen
        clues_here = engine.visit_location(chosen)
        st.session_state._last_clues = clues_here

    if c2.button("⬅ Go Back"):
        prev = engine.go_back()
        st.session_state.current_location = prev

    st.write("**Room history (stack, top = current):**")
    st.code(" ← ".join(reversed(engine.history.history())) or "(empty)")

    if st.session_state.current_location:
        loc = st.session_state.current_location
        st.subheader(f"📍 {loc}")
        clues = engine.locations.get(loc, [])
        if not clues:
            st.info("Nothing of interest here.")
        for clue in clues:
            found = clue.id in engine.found_clue_ids
            label = f"✅ {clue.description}" if found else f"🔍 {clue.description}"
            if st.button(label, key=f"clue_{clue.id}", disabled=found):
                engine.collect_clue(clue)
                st.rerun()

# ===========================================================================
# RELATIONSHIP WEB — GRAPH (BFS / DFS)
# ===========================================================================
elif page == "Relationship Web (Graph)":
    st.header("Relationship Web")
    st.caption("People are nodes, relationships are edges — a classic **graph**.")

    for name in list(engine.suspects.keys()) + [engine.victim]:
        rels = engine.graph.relations_of(name)
        if rels:
            st.write(f"**{name}** → " + ", ".join(f"{n} ({r})" for n, r in rels))

    st.markdown("---")
    st.subheader("Shortest connection to the victim (BFS)")
    who = st.selectbox("Suspect:", list(engine.suspects.keys()), key="bfs_who")
    if st.button("Find shortest path"):
        path = engine.graph.bfs_path(who, engine.victim)
        st.success(" → ".join(path) if path else "No connection found.")

    st.subheader("Who they're connected to within N hops (DFS)")
    depth = st.slider("Hops", 1, 3, 2)
    if st.button("Explore connections"):
        conns = engine.graph.dfs_connections(who, depth=depth)
        if conns:
            for name, relation, hop in conns:
                st.write(f"- {'—' * hop} **{name}** ({relation}), {hop} hop(s) away")
        else:
            st.info("No connections found at this depth.")

# ===========================================================================
# INTERROGATION — QUEUE
# ===========================================================================
elif page == "Interrogation Queue":
    st.header("Interrogation Room")
    st.caption("Suspects wait their turn in a **FIFO queue**.")

    st.write("**Waiting to be interrogated:**", ", ".join(engine.queue.upcoming()) or "(none left)")

    if st.button("Call in next suspect"):
        nxt = engine.interrogate_next()
        if nxt:
            st.session_state.interrogated.append(nxt)
        else:
            st.warning("No one left in the queue.")

    if st.session_state.interrogated:
        current = st.session_state.interrogated[-1]
        s = engine.suspects[current]
        st.subheader(f"Interrogating: {current}")
        st.write(f"**Alibi:** {s.alibi}")
        st.write(f"**Motive:** {s.motive}")
        st.write("**Evidence on file:**")
        for c in engine.locker.get(current):
            st.write(f"- {c.description}")
        if not engine.locker.get(current):
            st.write("- (none collected yet)")

    st.markdown("---")
    st.write("**Already interrogated (in order):**", " → ".join(st.session_state.interrogated) or "(none yet)")

# ===========================================================================
# EVIDENCE LOCKER — HASH MAP
# ===========================================================================
elif page == "Evidence Locker (Hash Map)":
    st.header("Evidence Locker")
    st.caption("Evidence is stored in a **hash map**: suspect name → list of clues (O(1) lookup).")

    for name in engine.suspects:
        items = engine.locker.get(name)
        with st.expander(f"{name} — {len(items)} item(s), weight {engine.locker.weight_of(name)}"):
            if items:
                for c in items:
                    st.write(f"- {c.description}")
            else:
                st.write("_No evidence collected yet._")

# ===========================================================================
# TIMELINE — BST
# ===========================================================================
elif page == "Timeline (BST)":
    st.header("Chronological Timeline")
    st.caption("Clues are inserted into a **binary search tree** keyed by timestamp; "
               "an in-order traversal produces the timeline for free.")

    timeline = engine.full_timeline()
    if not timeline:
        st.info("No clues collected yet — go explore the estate.")
    else:
        for c in timeline:
            h, m = divmod(c.time, 60)
            st.write(f"**{h:02d}:{m:02d}** — {c.description}  _(points to {c.points_to})_")

    st.markdown("---")
    st.subheader("Range query")
    col1, col2 = st.columns(2)
    start_h = col1.slider("From hour", 0, 23, 18)
    end_h = col2.slider("To hour", 0, 23, 22)
    ranged = engine.timeline_between(start_h * 60, end_h * 60)
    st.write(f"Found {len(ranged)} clue(s) in that window.")
    for c in ranged:
        st.write(f"- {c.description}")

# ===========================================================================
# SUSPICION RANKING — HEAP
# ===========================================================================
elif page == "Suspicion Ranking (Heap)":
    st.header("Live Suspicion Ranking")
    st.caption("Suspicion scores are kept in a **max-heap (priority queue)** for O(log n) updates "
               "as new evidence comes in.")

    top = engine.heap.top()
    if top:
        st.metric("Prime suspect right now", top[0], f"suspicion {top[1]}")

    st.subheader("Full ranking (heap contents)")
    ranking = engine.suspicion_ranking()
    if not ranking:
        st.info("Collect some clues first.")
    for i, (name, score) in enumerate(ranking, start=1):
        st.write(f"{i}. **{name}** — suspicion score: {score}")

    st.markdown("---")
    st.subheader("Sorted leaderboard (plain sort, for comparison)")
    for i, (name, score) in enumerate(engine.sorted_leaderboard(), start=1):
        st.write(f"{i}. {name}: {score}")

# ===========================================================================
# ACCUSATION
# ===========================================================================
elif page == "Make an Accusation":
    st.header("⚖️ Make Your Accusation")
    st.warning("This ends the game. Make sure you've gathered enough evidence.")

    accused = st.selectbox("Who is the murderer?", list(engine.suspects.keys()))
    if st.button("Accuse", type="primary"):
        correct, message = engine.accuse(accused)
        if correct:
            st.success(message)
            st.balloons()
        else:
            st.error(message)

    if engine.solved:
        st.markdown("---")
        st.subheader("Case summary")
        for name, score in engine.sorted_leaderboard():
            st.write(f"- {name}: suspicion weight {score}")
