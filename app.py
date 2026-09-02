"""
Murder Mystery - The Detective Challenge
Streamlit frontend for game_engine.py

Run locally:
    streamlit run app.py
"""

import streamlit as st
import graphviz
from game_engine import MysteryGame, ACTIONS, QUESTIONS, compute_score

st.set_page_config(page_title="The Detective Challenge", page_icon="🕵️", layout="wide")

# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
if "game" not in st.session_state:
    st.session_state.game = MysteryGame()
if "stage" not in st.session_state:
    st.session_state.stage = "home"          # home -> playing -> scored
if "view" not in st.session_state:
    st.session_state.view = "Briefing"
if "last_reveal" not in st.session_state:
    st.session_state.last_reveal = None
if "last_answer" not in st.session_state:
    st.session_state.last_answer = None
if "result" not in st.session_state:
    st.session_state.result = None
if "score" not in st.session_state:
    st.session_state.score = None
if "breakdown" not in st.session_state:
    st.session_state.breakdown = None
if "reasoning" not in st.session_state:
    st.session_state.reasoning = ""

game: MysteryGame = st.session_state.game

# ---------------------------------------------------------------------------
# Theme (noir detective board — shared across every screen)
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

.case-card, .suspect-card, .home-card {
    background: linear-gradient(145deg, #23201b, #17140f);
    border: 1px solid #4a3f2c;
    border-radius: 12px;
    padding: 18px;
    box-shadow: 0 4px 14px rgba(0,0,0,0.5);
    margin-bottom: 12px;
}
.suspect-card { text-align: center; height: 100%; }
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
    display: inline-block; padding: 3px 10px; border-radius: 20px;
    font-size: 12px; font-weight: bold; margin: 2px 0;
}
.badge-found { background: #2e5d3a; color: #b7f0c2; }
.badge-hidden { background: #3a2e2e; color: #d9a3a3; }
.badge-warn { background: #6b3a1f; color: #ffd9a8; }
.badge-critical { background: #5d2e2e; color: #f0b7b7; }
.meter-track { background: #2b2620; border-radius: 8px; height: 16px; overflow: hidden; border: 1px solid #4a3f2c; }
.meter-fill { height: 100%; border-radius: 8px 0 0 8px; background: linear-gradient(90deg, #7a2e2e, #c9453f, #e8834a); }
.action-btn button { width: 100%; height: 80px; font-size: 17px !important; border-radius: 12px !important;
    border: 1px solid #4a3f2c !important; background: linear-gradient(145deg, #23201b, #17140f) !important;
    color: #e8e0d0 !important; }
.timeline-item { border-left: 3px solid #e8c37a; padding-left: 16px; margin-bottom: 18px; position: relative; }
.timeline-item::before { content: ''; position: absolute; left: -8px; top: 4px; width: 13px; height: 13px;
    background: #e8c37a; border-radius: 50%; }
.stButton>button { border-radius: 8px; }
.big-title { font-size: 48px; text-align: center; margin-bottom: 0; }
.tagline { text-align: center; }
.contradiction-box { background: #5d2e2e; border: 1px solid #c9453f; border-radius: 8px; padding: 10px 14px;
    font-weight: bold; color: #ffd9d9; margin-top: 8px; }
</style>
""", unsafe_allow_html=True)

AVATAR_DEFAULT = "🕵️"


def suspect_card_html(s, hide_details=False):
    motive = "❓ Unknown — interrogate this suspect first." if hide_details else s.motive
    alibi = "❓ Unknown — interrogate this suspect first." if hide_details else s.alibi
    return f"""
    <div class='suspect-card'>
        <div class='avatar-circle'>{s.avatar}</div>
        <h4 style='margin-bottom:2px'>{s.name}</h4>
        <p class='subtle' style='margin-top:0'>{s.relationship} · Age {s.age}</p>
        <p style='font-size:13px'><b>Personality:</b> {s.personality}</p>
        <p style='font-size:13px'><b>Motive:</b><br>{motive}</p>
        <p style='font-size:13px'><b>Alibi:</b><br>{alibi}</p>
    </div>
    """


def reset_to_home():
    st.session_state.stage = "home"
    st.session_state.view = "Briefing"
    st.session_state.last_reveal = None
    st.session_state.last_answer = None
    st.session_state.result = None
    st.session_state.score = None
    st.session_state.breakdown = None
    st.session_state.reasoning = ""


# ===========================================================================
# HOME SCREEN
# ===========================================================================
if st.session_state.stage == "home":
    st.markdown("<p class='big-title'>🕵️ Murder Mystery</p>", unsafe_allow_html=True)
    st.markdown("<h2 class='tagline'>The Detective Challenge</h2>", unsafe_allow_html=True)
    st.markdown(
        "<p class='subtle' style='text-align:center'>Four murders. Four mansions of secrets. "
        "Only one detective's badge is on the line — yours.</p>",
        unsafe_allow_html=True,
    )

    with st.expander("📖 How to Play (Instructions)"):
        st.markdown("""
- **Investigate**: choose actions like 🔎 Search Room, 📱 Check Phone, 🎥 Check CCTV, 📝 Read Messages,
  🩸 Examine Weapon, and 👣 Check Fingerprints to reveal clues.
- **Not every clue is real** — some are misleading and get debunked later. Keep investigating before you trust one.
- **Interrogate** suspects with fixed questions. If a clue contradicts their answer, you'll see a
  ⚠️ **Contradiction detected!** warning.
- **Suspicion Meter** updates live as you gather evidence.
- **Evidence Board** visually connects the victim, suspects, clues, and motives.
- **Final Accusation**: name the murderer, the motive, the weapon, and explain your reasoning.
- **Score**: +10 per important clue (max 2 counted), +50 correct murderer / −30 if wrong,
  +20 correct motive, +10 correct weapon — out of 100.
        """)

    st.markdown("### 🎚️ Choose Your Difficulty")
    difficulty = st.radio(
        "Difficulty",
        ["Easy", "Medium", "Hard"],
        horizontal=True,
        label_visibility="collapsed",
        help="Easy: suspicion scores + hints shown. Medium: scores shown, no hints. "
             "Hard: suspect motives/alibis hidden until interrogated, suspicion meter shows bars only.",
    )
    st.session_state.pending_difficulty = difficulty

    st.markdown("### 🗂️ Choose a Case")
    cols = st.columns(4)
    for col, (cid, case) in zip(cols, game.cases.items()):
        with col:
            st.markdown(
                f"""
                <div class='home-card' style='text-align:center'>
                    <div style='font-size:44px'>{case.icon}</div>
                    <h4>{case.title}</h4>
                    <p style='font-size:13px'>{case.description}</p>
                </div>
                """,
                unsafe_allow_html=True,
            )
            if st.button(f"▶️ Start Game", key=f"start_{cid}", use_container_width=True):
                game.start(cid, st.session_state.pending_difficulty)
                st.session_state.stage = "playing"
                st.session_state.view = "Briefing"
                st.rerun()

# ===========================================================================
# PLAYING / SCORED
# ===========================================================================
else:
    case = game.case
    difficulty = game.difficulty

    st.markdown(f"<h1>{case.icon} {case.title}</h1>", unsafe_allow_html=True)
    st.caption(f"Difficulty: **{difficulty}**")

    hud1, hud2, hud3, hud4 = st.columns(4)
    hud1.metric("🧩 Clues Found", f"{len(case.found_clue_ids)}/6")
    hud2.metric("🗣️ Interrogated", f"{len(case.interrogated_suspects)}/4")
    top = case.heap.top()
    hud3.metric("🎯 Prime Suspect", top[0] if top else "Unknown")
    hud4.metric("🔧 Actions Used", f"{len(case.actions_done)}/6")
    st.progress(len(case.found_clue_ids) / 6)
    st.markdown("---")

    st.sidebar.markdown("### 🗺️ Investigation Menu")
    nav_items = [
        ("Briefing", "📁"),
        ("Suspects", "👥"),
        ("Investigate", "🔍"),
        ("Interrogation", "🤖"),
        ("Evidence Locker", "🗃️"),
        ("Timeline", "⏳"),
        ("Suspicion Meter", "📊"),
        ("Evidence Board", "🧷"),
        ("Final Accusation", "⚖️"),
    ]
    for label, icon in nav_items:
        if st.sidebar.button(f"{icon}  {label}", use_container_width=True):
            st.session_state.view = label
    st.sidebar.markdown("---")
    if st.sidebar.button("🏠 Back to Home / New Case", use_container_width=True):
        reset_to_home()
        st.rerun()

    view = st.session_state.view

    # -----------------------------------------------------------------
    # BRIEFING
    # -----------------------------------------------------------------
    if view == "Briefing":
        st.markdown(
            f"<div class='case-card'>💀 <b>Victim:</b> {case.victim}<br><br>{case.description}</div>",
            unsafe_allow_html=True,
        )
        st.info("👉 Head to **Investigate** to start searching for clues, then **Interrogation** "
                "once you have some evidence to test suspects' stories against.")

    # -----------------------------------------------------------------
    # SUSPECTS
    # -----------------------------------------------------------------
    elif view == "Suspects":
        st.header("👥 Suspect Profiles")
        hide = (difficulty == "Hard")
        cols = st.columns(4)
        for col, (name, s) in zip(cols, case.suspects.items()):
            with col:
                hide_this = hide and name not in case.interrogated_suspects
                st.markdown(suspect_card_html(s, hide_details=hide_this), unsafe_allow_html=True)
        if hide:
            st.caption("🔒 Hard mode: motives and alibis stay hidden until you interrogate that suspect.")

    # -----------------------------------------------------------------
    # INVESTIGATE
    # -----------------------------------------------------------------
    elif view == "Investigate":
        st.header("🔍 Investigation Actions")
        st.caption("Every action you take is logged on a **stack** (see the trail below).")

        grid = st.columns(3)
        for i, (action_key, label) in enumerate(ACTIONS):
            with grid[i % 3]:
                st.markdown("<div class='action-btn'>", unsafe_allow_html=True)
                done = action_key in case.actions_done
                btn_label = f"{label}\n✅ done" if done else label
                if st.button(btn_label, key=f"act_{action_key}"):
                    clue = case.perform_action(action_key)
                    st.session_state.last_reveal = clue
                    if clue:
                        st.toast(f"🧩 New clue discovered!")
                    st.rerun()
                st.markdown("</div>", unsafe_allow_html=True)

        if difficulty == "Easy":
            remaining = [label for key, label in ACTIONS if key not in case.actions_done]
            if remaining:
                st.info(f"💡 Hint: you haven't tried **{remaining[0]}** yet.")

        st.markdown(
            f"<p class='subtle'>🧭 Action trail: {' → '.join(case.stack.history()) or '(none yet)'}</p>",
            unsafe_allow_html=True,
        )

        if st.session_state.last_reveal:
            c = st.session_state.last_reveal
            st.markdown(
                f"<div class='case-card'><span class='badge badge-found'>NEW CLUE</span><br><br>{c.description}</div>",
                unsafe_allow_html=True,
            )

        st.markdown("---")
        st.subheader("📋 All clues found so far")
        if not case.found_clue_ids:
            st.caption("Nothing found yet — try an action above.")
        for c in case.clues:
            if c.id not in case.found_clue_ids:
                continue
            debunked = c.id in case.debunked_ids
            badge = "<span class='badge badge-warn'>⚠️ DEBUNKED — later shown unreliable</span>" if debunked else (
                "<span class='badge badge-critical'>🔑 KEY EVIDENCE</span>" if c.critical else "<span class='badge badge-found'>EVIDENCE</span>"
            )
            text = f"<s>{c.description}</s>" if debunked else c.description
            st.markdown(f"<div class='case-card'>{badge}<br><br>{text}</div>", unsafe_allow_html=True)

    # -----------------------------------------------------------------
    # INTERROGATION
    # -----------------------------------------------------------------
    elif view == "Interrogation":
        st.header("🤖 AI Interrogation System")
        st.caption("Pick a suspect and a question. If evidence you've found contradicts their answer, "
                   "you'll be warned instantly.")

        colA, colB = st.columns(2)
        with colA:
            st.markdown(
                f"<p class='subtle'>Queue (FIFO): {' → '.join(case.queue.upcoming()) or '(empty)'}</p>",
                unsafe_allow_html=True,
            )
            if st.button("📣 Call in next suspect from queue"):
                nxt = case.interrogate_next()
                if nxt:
                    st.session_state.current_suspect = nxt
                else:
                    st.warning("No one left in the queue.")
        with colB:
            chosen = st.selectbox("...or pick a suspect directly:", list(case.suspects.keys()))
            st.session_state.current_suspect = chosen

        current = st.session_state.get("current_suspect")
        if current:
            s = case.suspects[current]
            st.markdown(
                f"""
                <div class='suspect-card' style='text-align:left; display:flex; gap:20px; align-items:flex-start;'>
                    <div class='avatar-circle' style='margin:0'>{s.avatar}</div>
                    <div><h3 style='margin:0'>{current}</h3><p class='subtle' style='margin:2px 0'>{s.relationship}</p></div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            q_labels = {qid: text for qid, text in QUESTIONS}
            qid = st.radio("Ask:", list(q_labels.keys()), format_func=lambda k: q_labels[k], key=f"q_{current}")
            if st.button("🎙️ Ask question", type="primary"):
                ans, contradiction = case.ask_question(current, qid)
                st.session_state.last_answer = (current, q_labels[qid], ans.text, contradiction)

            if st.session_state.last_answer and st.session_state.last_answer[0] == current:
                _, qtext, atext, contradiction = st.session_state.last_answer
                st.markdown(f"**🗨️ \"{qtext}\"**")
                st.markdown(f"> {atext}")
                if contradiction:
                    st.markdown(
                        "<div class='contradiction-box'>⚠️ Contradiction detected! "
                        "Evidence you've found conflicts with this answer.</div>",
                        unsafe_allow_html=True,
                    )

    # -----------------------------------------------------------------
    # EVIDENCE LOCKER
    # -----------------------------------------------------------------
    elif view == "Evidence Locker":
        st.header("🗃️ Evidence Locker")
        st.caption("A **hash map**: suspect name → list of clues (O(1) lookup). Debunked clues no longer count.")

        cols = st.columns(4)
        for col, name in zip(cols, case.suspects):
            items = case.locker.get(name)
            weight = case.effective_weight(name)
            with col:
                st.markdown(
                    f"""<div class='suspect-card'><div class='avatar-circle'>{case.suspects[name].avatar}</div>
                    <h4>{name}</h4><p class='subtle'>{len(items)} item(s) · weight {weight}</p></div>""",
                    unsafe_allow_html=True,
                )
                with st.expander("View evidence"):
                    if items:
                        for c in items:
                            tag = " ⚠️ (debunked)" if c.id in case.debunked_ids else ""
                            st.write(f"- {c.description}{tag}")
                    else:
                        st.caption("No evidence collected yet.")

    # -----------------------------------------------------------------
    # TIMELINE
    # -----------------------------------------------------------------
    elif view == "Timeline":
        st.header("⏳ Chronological Timeline")
        st.caption("Clues sit in a **binary search tree** keyed by time; in-order traversal gives the timeline for free.")
        timeline = case.full_timeline()
        if not timeline:
            st.info("No clues collected yet.")
        for c in timeline:
            h, m = divmod(c.time, 60)
            tag = " ⚠️ later debunked" if c.id in case.debunked_ids else ""
            st.markdown(
                f"<div class='timeline-item'><b>{h:02d}:{m:02d}</b> — {c.description}{tag}"
                f"<br><span class='subtle'>points to {c.points_to}</span></div>",
                unsafe_allow_html=True,
            )

    # -----------------------------------------------------------------
    # SUSPICION METER
    # -----------------------------------------------------------------
    elif view == "Suspicion Meter":
        st.header("📊 Live Suspicion Meter")
        st.caption("Scores live in a **max-heap (priority queue)** — updated after every action.")

        ranking = case.suspicion_ranking()
        max_score = max([sc for _, sc in ranking] + [1])
        for name, score in ranking:
            pct = int(100 * score / max_score) if max_score else 0
            label = f"**{case.suspects[name].avatar} {name}**" + (f" — {score}" if difficulty != "Hard" else "")
            st.markdown(label)
            st.markdown(
                f"<div class='meter-track'><div class='meter-fill' style='width:{pct}%'></div></div><br>",
                unsafe_allow_html=True,
            )

    # -----------------------------------------------------------------
    # EVIDENCE BOARD
    # -----------------------------------------------------------------
    elif view == "Evidence Board":
        st.header("🧷 Evidence Board")
        st.caption("Victim → Suspects → Clues → Motives, all connected in one board.")

        dot = graphviz.Digraph()
        dot.attr(bgcolor="transparent", rankdir="LR")
        dot.attr("node", style="filled", fontname="Helvetica", fontcolor="white")
        dot.node("VICTIM", case.victim, shape="octagon", fillcolor="#7a2e2e", color="#e8c37a")

        for name, s in case.suspects.items():
            dot.node(name, f"{s.avatar}\n{name}", shape="box", fillcolor="#2c2620", color="#e8c37a")
            for _, rel in case.graph.relations_of(case.victim):
                pass
            rel_label = next((r for n, r in case.graph.relations_of(case.victim) if n == name), "connected")
            dot.edge("VICTIM", name, label=rel_label, fontsize="9", fontcolor="#b8ab90", color="#6b5c40")

            motive_id = f"MOTIVE_{name}"
            dot.node(motive_id, f"🎯 {s.motive[:35]}...", shape="note", fillcolor="#33291c", color="#e8c37a", fontsize="9")
            dot.edge(name, motive_id, style="dashed", color="#6b5c40")

            for c in case.locker.get(name):
                clue_id = f"CLUE_{c.id}"
                style = "dotted" if c.id in case.debunked_ids else "solid"
                fill = "#3a2e2e" if c.id in case.debunked_ids else "#1f3d28"
                dot.node(clue_id, f"🧩 {c.description[:40]}...", shape="ellipse", fillcolor=fill, color="#e8c37a", fontsize="8")
                dot.edge(name, clue_id, style=style, color="#6b5c40")

        st.graphviz_chart(dot, use_container_width=True)

    # -----------------------------------------------------------------
    # FINAL ACCUSATION
    # -----------------------------------------------------------------
    elif view == "Final Accusation":
        st.header("⚖️ Make Your Final Accusation")

        if st.session_state.result is None:
            st.warning("This ends the game. Make sure you've investigated and interrogated first.")
            murderer = st.selectbox("🕵️ Who is the murderer?", list(case.suspects.keys()))
            motive = st.selectbox("🎯 What was the motive?", case.motive_options)
            weapon = st.selectbox("🔪 What was the murder weapon?", case.weapon_options)
            reasoning = st.text_area("📝 Explain your reasoning:", value=st.session_state.reasoning, height=120)

            if st.button("🚨 Submit Accusation", type="primary"):
                st.session_state.reasoning = reasoning
                result = case.accuse(murderer, motive, weapon)
                score, breakdown = compute_score(case, result)
                st.session_state.result = result
                st.session_state.score = score
                st.session_state.breakdown = breakdown
                st.session_state.stage = "scored"
                st.rerun()
        else:
            result = st.session_state.result
            if result["murderer_correct"]:
                st.success(f"✅ Correct! **{result['actual_murderer']}** was the murderer.")
                st.balloons()
            else:
                st.error(f"❌ Incorrect. You accused **{result['accused']}**, but the real murderer was "
                         f"**{result['actual_murderer']}**.")

            st.write(f"🎯 Motive: {'✅ Correct' if result['motive_correct'] else '❌ Incorrect'}")
            st.write(f"🔪 Weapon: {'✅ Correct' if result['weapon_correct'] else '❌ Incorrect'}")

            if st.session_state.reasoning:
                st.markdown(f"**Your reasoning:** _{st.session_state.reasoning}_")

            st.markdown("---")
            st.markdown(f"## 🏆 Detective Score: {st.session_state.score}/100")
            for k, v in st.session_state.breakdown.items():
                sign = "+" if v >= 0 else ""
                st.write(f"- {k}: {sign}{v}")

            st.markdown("---")
            c1, c2 = st.columns(2)
            if c1.button("🔁 Play This Case Again", use_container_width=True):
                game.start(case.id, difficulty)
                st.session_state.view = "Briefing"
                st.session_state.result = None
                st.session_state.score = None
                st.session_state.breakdown = None
                st.session_state.reasoning = ""
                st.session_state.stage = "playing"
                st.rerun()
            if c2.button("🏠 New Case", use_container_width=True):
                reset_to_home()
                st.rerun()
