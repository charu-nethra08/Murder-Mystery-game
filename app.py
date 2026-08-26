"""
Murder Mystery: The Blackwood Case
Visual Streamlit frontend for game_engine.py

Run locally:
    streamlit run app.py
"""

import streamlit as st
import graphviz
from game_engine import GameEngine

st.set_page_config(page_title="The Blackwood Case", page_icon="🔎", layout="wide")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "engine" not in st.session_state:
    st.session_state.engine = GameEngine()
if "current_location" not in st.session_state:
    st.session_state.current_location = None
if "interrogated" not in st.session_state:
    st.session_state.interrogated = []
if "page" not in st.session_state:
    st.session_state.page = "Case Overview"

engine: GameEngine = st.session_state.engine

# ---------------------------------------------------------------------------
# Visual constants
# ---------------------------------------------------------------------------
AVATARS = {
    "Eleanor Blackwood": "🤵‍♀️",
    "James Carter": "💼",
    "Sophia Reyes": "🧹",
    "Marcus Whitfield": "🚬",
    "Dr. Victor Lang": "🩺",
}
ROOM_ICONS = {
    "Library": "📚",
    "Kitchen": "🍳",
    "Study": "🗂️",
    "Garden": "🌳",
    "Bedroom": "🛏️",
    "Dining Room": "🍽️",
}

# ---------------------------------------------------------------------------
# Theme (noir detective board)
# ---------------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700;900&family=Special+Elite&display=swap');

.stApp {
    background: radial-gradient(circle at top, #1a1410 0%, #0c0a08 60%);
    color: #e8e0d0;
}
h1, h2, h3 { font-family: 'Playfair Display', serif !important; color: #e8c37a !important; }
.subtle { font-family: 'Special Elite', monospace; color: #b8ab90; }

.case-card {
    background: linear-gradient(145deg, #23201b, #17140f);
    border: 1px solid #4a3f2c;
    border-radius: 10px;
    padding: 16px 18px;
    margin-bottom: 12px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.5);
}
.suspect-card {
    background: linear-gradient(145deg, #23201b, #17140f);
    border: 1px solid #4a3f2c;
    border-radius: 12px;
    padding: 18px;
    text-align: center;
    box-shadow: 0 4px 14px rgba(0,0,0,0.5);
    height: 100%;
}
.avatar-circle {
    font-size: 46px;
    background: #2c2620;
    border: 2px solid #e8c37a;
    border-radius: 50%;
    width: 80px; height: 80px;
    display: flex; align-items: center; justify-content: center;
    margin: 0 auto 10px auto;
}
.badge {
    display: inline-block;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 12px;
    font-weight: bold;
    margin: 2px 0;
}
.badge-found { background: #2e5d3a; color: #b7f0c2; }
.badge-hidden { background: #3a2e2e; color: #d9a3a3; }
.meter-track {
    background: #2b2620; border-radius: 8px; height: 16px; overflow: hidden;
    border: 1px solid #4a3f2c;
}
.meter-fill {
    height: 100%; border-radius: 8px 0 0 8px;
    background: linear-gradient(90deg, #7a2e2e, #c9453f, #e8834a);
}
.room-btn button {
    width: 100%;
    height: 90px;
    font-size: 20px !important;
    border-radius: 12px !important;
    border: 1px solid #4a3f2c !important;
    background: linear-gradient(145deg, #23201b, #17140f) !important;
    color: #e8e0d0 !important;
}
.timeline-item {
    border-left: 3px solid #e8c37a;
    padding-left: 16px;
    margin-bottom: 18px;
    position: relative;
}
.timeline-item::before {
    content: '';
    position: absolute;
    left: -8px; top: 4px;
    width: 13px; height: 13px;
    background: #e8c37a;
    border-radius: 50%;
}
.stButton>button {
    border-radius: 8px;
}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1>🔎 The Blackwood Case</h1>", unsafe_allow_html=True)
st.markdown(
    "<p class='subtle'>Edmund Blackwood is dead. Five suspects. One estate. "
    "Explore rooms, gather evidence, follow the connections, and name your killer.</p>",
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Top progress bar (always visible — makes it feel like a game HUD)
# ---------------------------------------------------------------------------
progress = len(engine.found_clue_ids) / 10
hud1, hud2, hud3 = st.columns(3)
hud1.metric("🧩 Clues Found", f"{len(engine.found_clue_ids)}/10")
hud2.metric("🗣️ Suspects Interrogated", f"{len(st.session_state.interrogated)}/5")
top = engine.heap.top()
hud3.metric("🎯 Prime Suspect", top[0] if top else "Unknown")
st.progress(progress)
st.markdown("---")

# ---------------------------------------------------------------------------
# Sidebar navigation — icon buttons instead of a plain radio list
# ---------------------------------------------------------------------------
st.sidebar.markdown("### 🗺️ Investigation Menu")
nav_items = [
    ("Case Overview", "📁"),
    ("Explore Locations (Stack)", "🏚️"),
    ("Relationship Web (Graph)", "🕸️"),
    ("Interrogation Queue", "🎙️"),
    ("Evidence Locker (Hash Map)", "🗃️"),
    ("Timeline (BST)", "⏳"),
    ("Suspicion Ranking (Heap)", "📊"),
    ("Make an Accusation", "⚖️"),
]
for label, icon in nav_items:
    if st.sidebar.button(f"{icon}  {label}", use_container_width=True):
        st.session_state.page = label
page = st.session_state.page
st.sidebar.markdown("---")
st.sidebar.caption(f"Current: **{page}**")

# ===========================================================================
# CASE OVERVIEW
# ===========================================================================
if page == "Case Overview":
    st.markdown(
        f"<div class='case-card'>💀 <b>Victim:</b> {engine.victim} — found dead in the "
        f"Library at 9:00 PM.</div>",
        unsafe_allow_html=True,
    )
    cols = st.columns(5)
    for col, (name, s) in zip(cols, engine.suspects.items()):
        with col:
            st.markdown(
                f"""
                <div class='suspect-card'>
                    <div class='avatar-circle'>{AVATARS[name]}</div>
                    <h4 style='margin-bottom:2px'>{name}</h4>
                    <p class='subtle' style='margin-top:0'>{s.role}</p>
                    <p style='font-size:13px'><b>Motive:</b><br>{s.motive}</p>
                    <p style='font-size:13px'><b>Alibi:</b><br>{s.alibi}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
    st.info("👉 Start in **Explore Locations** to search rooms for clues, then check the "
            "**Relationship Web** and **Suspicion Ranking** as you go.")

# ===========================================================================
# EXPLORE LOCATIONS — visual room map (STACK)
# ===========================================================================
elif page == "Explore Locations (Stack)":
    st.header("🏚️ Explore the Estate")
    st.caption("Click a room to search it. Your path is remembered on a **stack** — 'Go Back' pops the last room.")

    rooms = list(engine.locations.keys())
    grid = st.columns(3)
    for i, room in enumerate(rooms):
        with grid[i % 3]:
            st.markdown("<div class='room-btn'>", unsafe_allow_html=True)
            n_found = sum(1 for c in engine.locations[room] if c.id in engine.found_clue_ids)
            n_total = len(engine.locations[room])
            label = f"{ROOM_ICONS.get(room,'🚪')}  {room}\n({n_found}/{n_total} clues found)" if n_total else f"{ROOM_ICONS.get(room,'🚪')}  {room}"
            if st.button(label, key=f"room_{room}"):
                st.session_state.current_location = room
                engine.visit_location(room)
            st.markdown("</div>", unsafe_allow_html=True)

    c1, c2 = st.columns([1, 4])
    if c1.button("⬅ Go Back"):
        prev = engine.go_back()
        st.session_state.current_location = prev

    st.markdown(
        f"<p class='subtle'>🧭 Path so far: "
        f"{' → '.join(engine.history.history()) or '(none yet)'}</p>",
        unsafe_allow_html=True,
    )

    if st.session_state.current_location:
        loc = st.session_state.current_location
        st.subheader(f"{ROOM_ICONS.get(loc,'🚪')} {loc}")
        clues = engine.locations.get(loc, [])
        if not clues:
            st.markdown("<div class='case-card'>Nothing of interest here.</div>", unsafe_allow_html=True)
        for clue in clues:
            found = clue.id in engine.found_clue_ids
            badge = "<span class='badge badge-found'>✅ COLLECTED</span>" if found else "<span class='badge badge-hidden'>🔍 UNDISCOVERED</span>"
            st.markdown(
                f"<div class='case-card'>{badge}<br><br>{clue.description}</div>",
                unsafe_allow_html=True,
            )
            if not found:
                if st.button("Collect this clue", key=f"clue_{clue.id}"):
                    engine.collect_clue(clue)
                    st.toast(f"🧩 New evidence filed against {clue.points_to}!")
                    st.rerun()

# ===========================================================================
# RELATIONSHIP WEB — rendered GRAPH (BFS / DFS)
# ===========================================================================
elif page == "Relationship Web (Graph)":
    st.header("🕸️ Relationship Web")
    st.caption("A real rendered **graph** — people are nodes, relationships are edges.")

    dot = graphviz.Graph()
    dot.attr(bgcolor="transparent")
    dot.attr("node", style="filled", fontname="Helvetica", fontcolor="white")
    dot.node(engine.victim, engine.victim, shape="octagon", fillcolor="#7a2e2e", color="#e8c37a")
    for name in engine.suspects:
        dot.node(name, f"{AVATARS[name]}\n{name}", shape="box", fillcolor="#2c2620", color="#e8c37a")
    seen_edges = set()
    for a, edges in engine.graph.adj.items():
        for b, relation in edges:
            key = tuple(sorted([a, b])) + (relation,)
            if key in seen_edges:
                continue
            seen_edges.add(key)
            dot.edge(a, b, label=relation, fontsize="10", fontcolor="#b8ab90", color="#6b5c40")
    st.graphviz_chart(dot, use_container_width=True)

    st.markdown("---")
    colA, colB = st.columns(2)
    with colA:
        st.subheader("🔗 Shortest connection to the victim")
        who = st.selectbox("Suspect:", list(engine.suspects.keys()), key="bfs_who")
        if st.button("Find shortest path (BFS)"):
            path = engine.graph.bfs_path(who, engine.victim)
            st.success(" → ".join(path) if path else "No connection found.")
    with colB:
        st.subheader("🌐 Who they're connected to")
        depth = st.slider("Hops", 1, 3, 2)
        if st.button("Explore connections (DFS)"):
            conns = engine.graph.dfs_connections(who, depth=depth)
            if conns:
                for name, relation, hop in conns:
                    st.write(f"{'—' * hop} **{name}** _({relation})_, {hop} hop(s) away")
            else:
                st.info("No connections found at this depth.")

# ===========================================================================
# INTERROGATION — chat-style QUEUE
# ===========================================================================
elif page == "Interrogation Queue":
    st.header("🎙️ Interrogation Room")
    st.caption("Suspects wait their turn in a **FIFO queue**.")

    st.markdown(
        f"<p class='subtle'>Waiting: {' → '.join(engine.queue.upcoming()) or '(none left)'}</p>",
        unsafe_allow_html=True,
    )

    if st.button("📣 Call in next suspect", type="primary"):
        nxt = engine.interrogate_next()
        if nxt:
            st.session_state.interrogated.append(nxt)
        else:
            st.warning("No one left in the queue.")

    if st.session_state.interrogated:
        current = st.session_state.interrogated[-1]
        s = engine.suspects[current]
        st.markdown(
            f"""
            <div class='suspect-card' style='text-align:left; display:flex; gap:20px; align-items:flex-start;'>
                <div class='avatar-circle' style='margin:0'>{AVATARS[current]}</div>
                <div>
                    <h3 style='margin:0'>{current}</h3>
                    <p class='subtle' style='margin:2px 0'>{s.role}</p>
                    <p>🗨️ <i>"{s.alibi}"</i></p>
                    <p><b>Suspected motive:</b> {s.motive}</p>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.write("**📂 Evidence on file against them:**")
        items = engine.locker.get(current)
        if items:
            for c in items:
                st.markdown(f"- {c.description}")
        else:
            st.caption("No evidence collected yet.")

    st.markdown("---")
    st.markdown(
        f"<p class='subtle'>✅ Already interrogated: {' → '.join(st.session_state.interrogated) or '(none yet)'}</p>",
        unsafe_allow_html=True,
    )

# ===========================================================================
# EVIDENCE LOCKER — HASH MAP
# ===========================================================================
elif page == "Evidence Locker (Hash Map)":
    st.header("🗃️ Evidence Locker")
    st.caption("Evidence is stored in a **hash map**: suspect name → list of clues (O(1) lookup).")

    cols = st.columns(len(engine.suspects))
    for col, name in zip(cols, engine.suspects):
        items = engine.locker.get(name)
        weight = engine.locker.weight_of(name)
        with col:
            st.markdown(
                f"""
                <div class='suspect-card'>
                    <div class='avatar-circle'>{AVATARS[name]}</div>
                    <h4>{name}</h4>
                    <p class='subtle'>{len(items)} item(s) · weight {weight}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            with st.expander("View evidence"):
                if items:
                    for c in items:
                        st.write(f"- {c.description}")
                else:
                    st.caption("No evidence collected yet.")

# ===========================================================================
# TIMELINE — visual vertical BST timeline
# ===========================================================================
elif page == "Timeline (BST)":
    st.header("⏳ Chronological Timeline")
    st.caption("Clues sit in a **binary search tree** keyed by timestamp; an in-order traversal "
               "gives the timeline for free, in O(n).")

    timeline = engine.full_timeline()
    if not timeline:
        st.info("No clues collected yet — go explore the estate.")
    else:
        for c in timeline:
            h, m = divmod(c.time, 60)
            st.markdown(
                f"<div class='timeline-item'><b>{h:02d}:{m:02d}</b> — {c.description} "
                f"<br><span class='subtle'>points to {c.points_to}</span></div>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.subheader("🔎 Range query")
    col1, col2 = st.columns(2)
    start_h = col1.slider("From hour", 0, 23, 18)
    end_h = col2.slider("To hour", 0, 23, 22)
    ranged = engine.timeline_between(start_h * 60, end_h * 60)
    st.write(f"Found **{len(ranged)}** clue(s) in that window.")
    for c in ranged:
        st.write(f"- {c.description}")

# ===========================================================================
# SUSPICION RANKING — visual meters via HEAP
# ===========================================================================
elif page == "Suspicion Ranking (Heap)":
    st.header("📊 Live Suspicion Ranking")
    st.caption("Scores live in a **max-heap (priority queue)** for O(log n) updates as evidence comes in.")

    ranking = engine.suspicion_ranking()
    max_score = max([s for _, s in ranking] + [1])

    if not ranking or max_score == 0:
        st.info("Collect some clues first to build suspicion.")
    else:
        top_name, top_score = ranking[0]
        st.markdown(
            f"<div class='case-card'>🎯 <b>Prime suspect right now:</b> "
            f"{AVATARS.get(top_name,'')} {top_name} (score {top_score})</div>",
            unsafe_allow_html=True,
        )
        for name, score in ranking:
            pct = int(100 * score / max_score) if max_score else 0
            st.markdown(f"**{AVATARS[name]} {name}** — {score}")
            st.markdown(
                f"<div class='meter-track'><div class='meter-fill' style='width:{pct}%'></div></div><br>",
                unsafe_allow_html=True,
            )

    st.markdown("---")
    st.subheader("Sorted leaderboard (plain sort, for comparison)")
    st.bar_chart({name: score for name, score in engine.sorted_leaderboard()})

# ===========================================================================
# ACCUSATION
# ===========================================================================
elif page == "Make an Accusation":
    st.header("⚖️ Make Your Accusation")
    st.warning("This ends the game. Make sure you've gathered enough evidence first.")

    cols = st.columns(5)
    accused = None
    for col, name in zip(cols, engine.suspects):
        with col:
            st.markdown(
                f"<div class='suspect-card'><div class='avatar-circle'>{AVATARS[name]}</div>"
                f"<h4>{name}</h4></div>",
                unsafe_allow_html=True,
            )
            if st.button("Accuse", key=f"accuse_{name}"):
                accused = name

    if accused:
        correct, message = engine.accuse(accused)
        if correct:
            st.success(message)
            st.balloons()
        else:
            st.error(message)

    if engine.solved:
        st.markdown("---")
        st.subheader("📁 Case summary")
        for name, score in engine.sorted_leaderboard():
            st.write(f"- {AVATARS[name]} {name}: suspicion weight {score}")
