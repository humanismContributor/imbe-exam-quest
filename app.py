"""IMBE Exam Quest: a learning game for International Management & Business Ethics (BFH)."""

import datetime as dt
import json
import random
import time
from pathlib import Path

import altair as alt
import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

st.set_page_config(page_title="IMBE Exam Quest", page_icon="🎓", layout="wide")

DATA = Path(__file__).parent / "data"
DEFAULT_EXAM_DATE = dt.date(2026, 11, 4)
LEVELS = ["Intern", "Trainee", "Analyst", "Consultant", "Manager", "Director", "Chief Ethics Officer"]
XP_PER_LEVEL = 250


@st.cache_data
def load():
    topics = json.loads((DATA / "topics.json").read_text(encoding="utf-8"))
    questions = json.loads((DATA / "questions.json").read_text(encoding="utf-8"))
    extras = json.loads((DATA / "extras.json").read_text(encoding="utf-8"))
    return topics, questions, extras


TOPICS, QUESTIONS, EXTRAS = load()
TOPIC = {t["id"]: t for t in TOPICS}
QBY = {q["id"]: q for q in QUESTIONS}
BE_IDS = [t["id"] for t in TOPICS if t["area"] == "Business Ethics"]
IM_IDS = [t["id"] for t in TOPICS if t["area"] != "Business Ethics"]


# ---------- state ----------

def init_state():
    defaults = {
        "xp": 0,
        "history": {},        # qid -> list of bools
        "stars": {},          # topic id -> best boss score (0-5)
        "boxes": {},          # flashcard index -> Leitner box 1..3
        "plan_done": [],
        "best_lightning": 0,
        "sorts_done": [],
        "matches_done": [],
        "exam_results": [],
        "exam_date": DEFAULT_EXAM_DATE.isoformat(),
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)


init_state()
S = st.session_state


def add_xp(n):
    S.xp += n


def record(qid, ok):
    S.history.setdefault(qid, []).append(bool(ok))
    if ok:
        add_xp(10)


def level():
    lv = min(S.xp // XP_PER_LEVEL, len(LEVELS) - 1)
    return lv, LEVELS[lv], S.xp % XP_PER_LEVEL


def wrong_ids():
    return [qid for qid, h in S.history.items() if h and not h[-1] and qid in QBY]


def accuracy(ids=None):
    vals = [h[-1] for qid, h in S.history.items() if h and (ids is None or qid in ids)]
    return (sum(vals) / len(vals)) if vals else None


# ---------- audio & visuals ----------

def speak(text, key, label="🔊 Listen"):
    """Browser text-to-speech (Web Speech API): no files, works offline in Chrome/Edge/Safari."""
    payload = json.dumps(text)
    components.html(
        f"""
<div style="font-family:sans-serif;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
  <button id="p{key}" style="padding:6px 12px;border-radius:8px;border:1px solid #888;cursor:pointer">{label}</button>
  <button id="s{key}" style="padding:6px 10px;border-radius:8px;border:1px solid #888;cursor:pointer">⏹ Stop</button>
  <label style="font-size:13px">speed
    <select id="r{key}"><option>0.85</option><option selected>1</option><option>1.15</option><option>1.3</option></select>
  </label>
</div>
<script>
const t = {payload};
document.getElementById("p{key}").onclick = () => {{
  const s = window.speechSynthesis; s.cancel();
  const u = new SpeechSynthesisUtterance(t);
  u.lang = "en-GB"; u.rate = parseFloat(document.getElementById("r{key}").value);
  const v = s.getVoices().find(v => v.lang && v.lang.startsWith("en"));
  if (v) u.voice = v;
  s.speak(u);
}};
document.getElementById("s{key}").onclick = () => window.speechSynthesis.cancel();
</script>""",
        height=46,
    )


def render_visual(v, key):
    st.markdown(f"**{v.get('title', '')}**")
    kind = v["type"]
    if kind == "dot":
        st.graphviz_chart(v["dot"], width="stretch")
    elif kind == "bars":
        rows = []
        for item in v["items"]:
            for i, s in enumerate(v["series"]):
                rows.append({"label": item[0], "series": s, "value": item[i + 1]})
        df = pd.DataFrame(rows)
        enc = dict(
            x=alt.X("label:N", sort=None, title=None, axis=alt.Axis(labelAngle=0)),
            y=alt.Y("value:Q", title=v.get("unit") or None),
            color=alt.Color("series:N", legend=alt.Legend(orient="top", title=None)),
            tooltip=["label", "series", "value"],
        )
        if len(v["series"]) > 1:
            enc["xOffset"] = "series:N"
        bars = alt.Chart(df).mark_bar(cornerRadiusTopLeft=4, cornerRadiusTopRight=4).encode(**enc)
        text = alt.Chart(df).mark_text(dy=-7, fontSize=12).encode(
            x=enc["x"], y="value:Q", text="value:Q", **({"xOffset": "series:N"} if "xOffset" in enc else {})
        )
        st.altair_chart((bars + text).properties(height=260), width="stretch")
    elif kind == "versus":
        a, b = st.columns(2)
        for col, side in ((a, v["left"]), (b, v["right"])):
            with col.container(border=True):
                st.markdown(f"**{side['title']}**")
                st.markdown("\n".join(f"- {x}" for x in side["items"]))
    elif kind == "table":
        st.dataframe(pd.DataFrame(v["rows"], columns=v["columns"]), hide_index=True, width="stretch")
        if v.get("note"):
            st.caption(v["note"])
    elif kind == "means":
        for lo, mid, hi in v["rows"]:
            c1, c2, c3 = st.columns([2, 2, 2])
            c1.markdown(f"<div style='text-align:right;color:#c0392b'>⬅ {lo} (deficiency)</div>", unsafe_allow_html=True)
            c2.markdown(f"<div style='text-align:center;font-weight:700;color:#1e8449'>{mid}</div>", unsafe_allow_html=True)
            c3.markdown(f"<div style='color:#c0392b'>{hi} (excess) ➡</div>", unsafe_allow_html=True)
        st.caption("The mean is relative to your ability and situation: courage looks different for a bookworm, a soldier or a martial-arts champion.")
    elif kind == "poles":
        for left, right, hint, group in v["rows"]:
            c1, c2, c3 = st.columns([2, 3, 2])
            c1.markdown(f"**{left}**")
            c2.markdown(f"<div style='text-align:center'>⟵ {hint} ⟶ <span style='font-size:11px;opacity:.7'>[{group}]</span></div>", unsafe_allow_html=True)
            c3.markdown(f"<div style='text-align:right'><b>{right}</b></div>", unsafe_allow_html=True)
    elif kind == "timeline":
        for when, what in v["items"]:
            st.markdown(f"- **{when}**: {what}")


# ---------- question widgets ----------

def option_label(q, i):
    return f"{'abc'[i]}) {q['o'][i]}"


def show_feedback(q, chosen):
    ok = chosen == q["a"]
    right = option_label(q, q["a"]).rstrip(".")
    if ok:
        st.success(f"✅ Correct: **{right}**. {q['x']}")
    else:
        st.error(f"❌ Correct answer: **{right}**. {q['x']}")
    if q.get("flag"):
        st.warning(f"🚩 Answer-key note: {q['flag']}")
    st.caption(f"Source: {q.get('s', '')}" + (f" · Sample exam {q['sample']}" if q.get("sample") else ""))
    return ok


def question_audio_text(q):
    return q["q"] + " " + " ".join(f"Option {'ABC'[i]}: {o}." for i, o in enumerate(q["o"]))


# ---------- sidebar ----------

with st.sidebar:
    st.title("🎓 IMBE Exam Quest")
    lv, title, into = level()
    st.metric("Level", f"{lv + 1} · {title}", f"{S.xp} XP")
    st.progress(into / XP_PER_LEVEL, text=f"{into}/{XP_PER_LEVEL} XP to next level")
    exam_date = st.date_input("Exam date", dt.date.fromisoformat(S.exam_date))
    S.exam_date = exam_date.isoformat()
    days = (exam_date - dt.date.today()).days
    st.info(f"⏳ **{days} day{'s' if days != 1 else ''}** until the exam" if days >= 0 else "Exam date has passed 🎉")
    page = st.radio(
        "Choose a mode",
        ["🏠 Home & plan", "🗺️ Quest map", "⚡ Lightning round", "🃏 Flashcards", "🧩 Sort it", "🔗 Match-up",
         "📝 Exam simulator", "🎯 Mistake review", "🚩 Traps & review questions"],
    )
    st.divider()
    st.caption("Progress lives in this browser session. Save it to keep it between visits:")
    keys = ["xp", "history", "stars", "boxes", "plan_done", "best_lightning", "sorts_done", "matches_done", "exam_results", "exam_date"]
    st.download_button("💾 Save progress", json.dumps({k: S[k] for k in keys}), "imbe_progress.json", "application/json")
    up = st.file_uploader("Load progress", type="json", label_visibility="collapsed")
    if up is not None and st.button("Restore loaded progress"):
        loaded = json.load(up)
        for k in keys:
            if k in loaded:
                S[k] = loaded[k]
        S.boxes = {str(k): v for k, v in S.boxes.items()}
        st.rerun()


# ---------- pages ----------

def page_home():
    st.title("🎓 IMBE Exam Quest")
    st.markdown(
        "A learning game for the **International Management & Business Ethics** exam (30% of the module) at BFH. "
        "It is built around the AS23 sample exam: **single-choice questions with three options**, about half on business ethics "
        "and half on international management, China and culture."
    )
    c = st.columns(4)
    c[0].metric("XP", S.xp)
    acc = accuracy()
    c[1].metric("Accuracy", f"{acc:.0%}" if acc is not None else "–")
    c[2].metric("Boss stars", f"{sum(1 for v in S.stars.values() if v >= 4)}/{len(TOPICS)}")
    c[3].metric("Questions seen", f"{len(S.history)}/{len(QUESTIONS)}")

    st.subheader("Topic mastery")
    rows = []
    for t in TOPICS:
        ids = [q["id"] for q in QUESTIONS if q["t"] == t["id"]]
        a = accuracy(ids)
        rows.append({"Topic": f"{t['emoji']} {t['title']}", "Area": t["area"], "Boss": "⭐" * S.stars.get(t["id"], 0) or "–",
                     "Accuracy": None if a is None else round(a * 100), "Seen": sum(1 for i in ids if i in S.history), "Questions": len(ids)})
    st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch",
                 column_config={"Accuracy": st.column_config.ProgressColumn("Accuracy %", min_value=0, max_value=100, format="%d%%")})

    st.subheader("📅 5-day plan")
    for d, day in enumerate(EXTRAS["plan"]):
        with st.expander(f"{day['day']}: {day['focus']}", expanded=(d == 0)):
            for i, task in enumerate(day["tasks"]):
                k = f"{d}-{i}"
                done = st.checkbox(task, value=k in S.plan_done, key=f"plan{k}")
                if done and k not in S.plan_done:
                    S.plan_done.append(k)
                    add_xp(15)
                elif not done and k in S.plan_done:
                    S.plan_done.remove(k)

    st.subheader("How to play")
    st.markdown(
        f"- **Quest map**: learn each of the {len(TOPICS)} topics (key points, diagrams, 🔊 narration), then beat its **boss battle** (4/5 = ⭐).\n"
        "- **Lightning round**: 10 rapid questions; streaks multiply your XP.\n"
        "- **Flashcards / Sort it / Match-up**: drill definitions, classifications and who-said-what.\n"
        "- **Exam simulator**: the real AS23 sample exam or a random 30-question mock against the clock.\n"
        "- **Mistake review**: everything you last got wrong, until it's gone.\n"
        "- 🚩 Four answers in the AS23 sample key **contradict the course material** (Q2, Q4, Q6, Q13). Each is flagged where it appears, and the game uses the answer the sources support."
    )


def page_quest():
    st.title("🗺️ Quest map")
    st.caption("Pick a topic: ⭐ = boss beaten (4/5+), 🔸 = attempted.")
    cols = st.columns(3)
    for i, t in enumerate(TOPICS):
        stars = S.stars.get(t["id"], 0)
        badge = "⭐" if stars >= 4 else ("🔸" if stars else "")
        if cols[i % 3].button(f"{t['emoji']} {t['title']} {badge}", key=f"tp{t['id']}", width="stretch"):
            S.topic = t["id"]
            S.pop("boss", None)
    tid = S.get("topic", TOPICS[0]["id"])
    t = TOPIC[tid]
    st.divider()
    st.header(f"{t['emoji']} {t['title']}")
    st.caption(f"{t['area']} · {t['week']} · Sources: {', '.join(t['sources'])}")
    learn, visual, boss = st.tabs(["📖 Learn", "🖼️ Visuals", "🐉 Boss battle"])
    with learn:
        st.markdown("**Audio lesson** (about 2 minutes):")
        speak(t["narration"], f"n{tid}", "▶ Play audio lesson")
        for p in t["points"]:
            st.markdown(f"- {p}")
    with visual:
        for j, v in enumerate(t.get("visuals", [])):
            with st.container(border=True):
                render_visual(v, f"{tid}{j}")
    with boss:
        pool = [q for q in QUESTIONS if q["t"] == tid]
        if "boss" not in S or S.boss["tid"] != tid:
            S.boss = {"tid": tid, "ids": [q["id"] for q in random.sample(pool, min(5, len(pool)))], "done": False}
        st.markdown(f"Answer **{len(S.boss['ids'])}** questions. Score 4+ for a ⭐ and +50 XP. Best so far: {S.stars.get(tid, 0)}/5")
        with st.form(f"boss{tid}"):
            answers = {}
            for n, qid in enumerate(S.boss["ids"], 1):
                q = QBY[qid]
                answers[qid] = st.radio(f"**{n}. {q['q']}**", range(3), format_func=lambda i, q=q: option_label(q, i), index=None, key=f"b{qid}")
            submitted = st.form_submit_button("⚔️ Submit answers")
        if submitted:
            score = 0
            for qid, ch in answers.items():
                q = QBY[qid]
                st.markdown(f"**{q['q']}**")
                ok = show_feedback(q, ch)
                record(qid, ok)
                score += ok
            S.stars[tid] = max(S.stars.get(tid, 0), score)
            if score >= 4:
                add_xp(50)
                st.balloons()
                st.success(f"🏆 Boss defeated: {score}/5! +50 XP bonus")
            else:
                st.info(f"Score {score}/5. Revise the Learn tab and try again.")
            if st.button("🔁 New boss battle"):
                S.pop("boss")
                st.rerun()


def page_lightning():
    st.title("⚡ Lightning round")
    st.caption("10 questions from all topics. Correct answers in a row build a streak multiplier; answer within 20 s for a speed bonus.")
    lr = S.get("lr")
    if lr is None or lr.get("finished"):
        if lr and lr.get("finished"):
            st.success(f"Round over: **{lr['correct']}/10** correct · **{lr['points']} points** (best: {S.best_lightning})")
        topics = st.multiselect("Topics (empty = all)", [t["id"] for t in TOPICS], format_func=lambda i: f"{TOPIC[i]['emoji']} {TOPIC[i]['title']}")
        if st.button("▶ Start round", type="primary"):
            pool = [q["id"] for q in QUESTIONS if not topics or q["t"] in topics]
            S.lr = {"ids": random.sample(pool, min(10, len(pool))), "i": 0, "correct": 0, "streak": 0, "points": 0,
                    "t0": time.time(), "answered": None, "finished": False}
            st.rerun()
        return
    q = QBY[lr["ids"][lr["i"]]]
    c = st.columns(4)
    c[0].metric("Question", f"{lr['i'] + 1}/{len(lr['ids'])}")
    c[1].metric("Points", lr["points"])
    c[2].metric("Streak", f"🔥 {lr['streak']}")
    c[3].metric("Multiplier", f"×{1 + min(lr['streak'], 4) * 0.5:.1f}")
    st.subheader(q["q"])
    st.caption(f"{TOPIC[q['t']]['emoji']} {TOPIC[q['t']]['title']}")
    if lr["answered"] is None:
        for i in range(3):
            if st.button(option_label(q, i), key=f"lr{lr['i']}{i}", width="stretch"):
                ok = i == q["a"]
                record(q["id"], ok)
                secs = time.time() - lr["t0"]
                if ok:
                    lr["streak"] += 1
                    lr["correct"] += 1
                    lr["points"] += int((100 + (50 if secs < 20 else 0)) * (1 + min(lr["streak"] - 1, 4) * 0.5))
                else:
                    lr["streak"] = 0
                lr["answered"] = i
                st.rerun()
        speak(question_audio_text(q), f"lrq{lr['i']}", "🔊 Read question")
    else:
        show_feedback(q, lr["answered"])
        if st.button("Next ➡", type="primary"):
            lr["i"] += 1
            lr["answered"] = None
            lr["t0"] = time.time()
            if lr["i"] >= len(lr["ids"]):
                lr["finished"] = True
                S.best_lightning = max(S.best_lightning, lr["points"])
                add_xp(lr["correct"] * 5)
                if lr["correct"] >= 8:
                    st.balloons()
            st.rerun()


def page_cards():
    st.title("🃏 Flashcards")
    cards = EXTRAS["flashcards"]
    tsel = st.selectbox("Deck", ["all"] + [t["id"] for t in TOPICS],
                        format_func=lambda i: "All topics" if i == "all" else f"{TOPIC[i]['emoji']} {TOPIC[i]['title']}")
    idx = [i for i, c in enumerate(cards) if tsel == "all" or c["t"] == tsel]
    box = lambda i: S.boxes.get(str(i), 1)
    counts = [sum(1 for i in idx if box(i) == b) for b in (1, 2, 3)]
    st.caption(f"Leitner boxes: 📕 new/again **{counts[0]}** · 📙 learning **{counts[1]}** · 📗 known **{counts[2]}**. Cards in lower boxes come up more often.")
    if S.get("card_deck") != tsel or S.get("card") not in idx:
        S.card_deck = tsel
        weights = [{1: 6, 2: 3, 3: 1}[box(i)] for i in idx]
        S.card = random.choices(idx, weights)[0]
        S.flipped = False
    c = cards[S.card]
    with st.container(border=True):
        st.caption(f"{TOPIC[c['t']]['emoji']} {TOPIC[c['t']]['title']} · box {box(S.card)}")
        st.markdown(f"### {c['f']}")
        if S.flipped:
            st.markdown(f"#### {c['b']}")
    speak(c["f"] + ". " + (c["b"] if S.flipped else ""), f"fc{S.card}{S.flipped}", "🔊 Read card")
    a, b, d = st.columns(3)
    if not S.flipped:
        if a.button("🔄 Flip", type="primary", width="stretch"):
            S.flipped = True
            st.rerun()
    else:
        def nxt(new_box):
            S.boxes[str(S.card)] = new_box
            weights = [{1: 6, 2: 3, 3: 1}[box(i)] for i in idx]
            choices = [i for i in idx if i != S.card] or idx
            S.card = random.choices(choices, [weights[idx.index(i)] for i in choices])[0]
            S.flipped = False
        if a.button("😕 Again", width="stretch"):
            nxt(1)
            st.rerun()
        if b.button("🙂 Almost", width="stretch"):
            nxt(2)
            st.rerun()
        if d.button("😎 Got it", width="stretch"):
            nxt(3)
            add_xp(3)
            st.rerun()


def page_sort():
    st.title("🧩 Sort it")
    sorts = EXTRAS["sorts"]
    n = st.selectbox("Challenge", range(len(sorts)), format_func=lambda i: ("✅ " if i in S.sorts_done else "") + sorts[i]["title"])
    sset = sorts[n]
    st.subheader(sset["title"])
    order = random.Random(n).sample(sset["items"], len(sset["items"]))
    with st.form(f"sort{n}"):
        picks = [st.radio(item, sset["bins"], index=None, horizontal=True, key=f"so{n}-{j}") for j, (item, _) in enumerate(order)]
        go = st.form_submit_button("Check")
    if go:
        right = 0
        for (item, b), p in zip(order, picks):
            ok = p == sset["bins"][b]
            right += ok
            st.markdown(f"{'✅' if ok else '❌'} **{item}** → {sset['bins'][b]}" + ("" if ok else f" *(you: {p or '—'})*"))
        st.metric("Score", f"{right}/{len(order)}")
        if right == len(order):
            st.balloons()
            if n not in S.sorts_done:
                S.sorts_done.append(n)
                add_xp(40)


def page_match():
    st.title("🔗 Match-up")
    ms = EXTRAS["matches"]
    n = st.selectbox("Set", range(len(ms)), format_func=lambda i: ("✅ " if i in S.matches_done else "") + ms[i]["title"])
    pairs = ms[n]["pairs"]
    defs = random.Random(100 + n).sample([p[1] for p in pairs], len(pairs))
    with st.form(f"match{n}"):
        picks = [st.selectbox(f"**{term}**", defs, index=None, key=f"m{n}-{j}", placeholder="Pick the match…") for j, (term, _) in enumerate(pairs)]
        go = st.form_submit_button("Check matches")
    if go:
        right = sum(p == d for p, (_, d) in zip(picks, pairs))
        for (term, d), p in zip(pairs, picks):
            st.markdown(f"{'✅' if p == d else '❌'} **{term}** → {d}")
        st.metric("Score", f"{right}/{len(pairs)}")
        if right == len(pairs):
            st.balloons()
            if n not in S.matches_done:
                S.matches_done.append(n)
                add_xp(40)


def page_exam():
    st.title("📝 Exam simulator")
    ex = S.get("exam")
    if ex is None:
        kind = st.radio("Exam", ["AS23 sample exam (29 questions)", "Random mock exam (30 questions: 15 ethics + 15 IM)"])
        minutes = st.number_input("Time limit (minutes)", 10, 120, 35)
        if st.button("▶ Start exam", type="primary"):
            if kind.startswith("AS23"):
                ids = [q["id"] for q in QUESTIONS if q.get("sample")]
            else:
                be = [q["id"] for q in QUESTIONS if q["t"] in BE_IDS]
                im = [q["id"] for q in QUESTIONS if q["t"] in IM_IDS]
                ids = random.sample(be, 15) + random.sample(im, 15)
                random.shuffle(ids)
            S.exam = {"ids": ids, "start": time.time(), "minutes": minutes, "kind": kind, "submitted": False}
            st.rerun()
        if S.exam_results:
            st.subheader("Previous attempts")
            st.dataframe(pd.DataFrame(S.exam_results), hide_index=True, width="stretch")
        return
    end = ex["start"] + ex["minutes"] * 60
    if not ex["submitted"]:
        components.html(f"""<div id=t style="font:600 20px sans-serif;padding:6px 0"></div><script>
        const end={end * 1000};function f(){{const s=Math.max(0,Math.round((end-Date.now())/1000));
        document.getElementById('t').textContent=(s>0?'⏱ ':'⌛ Time is up! ')+Math.floor(s/60)+':'+String(s%60).padStart(2,'0')+' left';}}
        f();setInterval(f,1000);</script>""", height=40)
        st.caption("Exam conditions: one answer per question, no feedback until you submit.")
        with st.form("exam_form"):
            answers = {}
            for n, qid in enumerate(ex["ids"], 1):
                q = QBY[qid]
                answers[qid] = st.radio(f"**{n}. {q['q']}**", range(3), format_func=lambda i, q=q: option_label(q, i), index=None, key=f"e{qid}")
            sub = st.form_submit_button("📨 Submit exam", type="primary")
        if sub:
            ex["answers"] = answers
            ex["submitted"] = True
            ex["used"] = round((time.time() - ex["start"]) / 60, 1)
            score = 0
            for qid, ch in answers.items():
                ok = ch == QBY[qid]["a"]
                record(qid, ok)
                score += ok
            ex["score"] = score
            S.exam_results.append({"when": dt.datetime.now().strftime("%d %b %H:%M"), "exam": ex["kind"][:22],
                                   "score": f"{score}/{len(ex['ids'])}", "pct": round(100 * score / len(ex["ids"])), "minutes": ex["used"]})
            add_xp(score * 5)
            st.rerun()
        if st.button("Abandon exam"):
            S.pop("exam")
            st.rerun()
        return
    n = len(ex["ids"])
    pct = ex["score"] / n
    st.metric("Result", f"{ex['score']}/{n} ({pct:.0%})", f"{ex['used']} of {ex['minutes']} min")
    (st.balloons() if pct >= 0.8 else None)
    by_topic = {}
    for qid in ex["ids"]:
        t = QBY[qid]["t"]
        by_topic.setdefault(t, [0, 0])
        by_topic[t][1] += 1
        by_topic[t][0] += ex["answers"][qid] == QBY[qid]["a"]
    df = pd.DataFrame([{"topic": f"{TOPIC[t]['emoji']} {TOPIC[t]['title']}", "score %": round(100 * a / b)} for t, (a, b) in by_topic.items()])
    st.altair_chart(alt.Chart(df).mark_bar().encode(x=alt.X("score %:Q", scale=alt.Scale(domain=[0, 100])), y=alt.Y("topic:N", sort="x", title=None),
                    color=alt.condition("datum['score %'] >= 75", alt.value("#2e9e5b"), alt.value("#d9534f"))).properties(height=28 * len(df)),
                    width="stretch")
    only_wrong = st.toggle("Show only mistakes", value=True)
    for k, qid in enumerate(ex["ids"], 1):
        q = QBY[qid]
        if only_wrong and ex["answers"][qid] == q["a"]:
            continue
        with st.container(border=True):
            st.markdown(f"**{k}. {q['q']}**")
            ch = ex["answers"][qid]
            st.caption(f"Your answer: {option_label(q, ch) if ch is not None else '— (blank)'}")
            show_feedback(q, ch)
    if st.button("🔁 New exam", type="primary"):
        S.pop("exam")
        st.rerun()


def page_mistakes():
    st.title("🎯 Mistake review")
    ids = wrong_ids()
    if not ids:
        st.success("No open mistakes. Play a lightning round or an exam first, or enjoy the clean slate. 🎉")
        return
    st.caption(f"{len(ids)} question(s) you last answered wrongly. Answer them correctly to clear them.")
    qid = S.get("mq") if S.get("mq") in ids else ids[0]
    S.mq = qid
    q = QBY[qid]
    st.subheader(q["q"])
    st.caption(f"{TOPIC[q['t']]['emoji']} {TOPIC[q['t']]['title']}")
    ch = st.radio("Your answer", range(3), format_func=lambda i: option_label(q, i), index=None, key=f"mr{qid}{len(S.history[qid])}")
    if ch is not None:
        ok = show_feedback(q, ch)
        if st.button("Next ➡", type="primary"):
            record(qid, ok)
            rest = [i for i in ids if i != qid]
            S.mq = random.choice(rest) if rest else None
            st.rerun()


def page_traps():
    st.title("🚩 Exam traps & review questions")
    t1, t2, t3 = st.tabs(["Exam traps", "Review questions (with model answers)", "Sample-exam key check"])
    with t1:
        for tr in EXTRAS["traps"]:
            st.markdown(f"- {tr}")
        speak(" ".join(x.replace("*", "") for x in EXTRAS["traps"]), "traps", "🔊 Listen to all traps")
    with t2:
        tsel = st.selectbox("Topic", ["all"] + [t["id"] for t in TOPICS], key="rvt",
                            format_func=lambda i: "All topics" if i == "all" else f"{TOPIC[i]['emoji']} {TOPIC[i]['title']}")
        for k, r in enumerate(EXTRAS["review"]):
            if tsel != "all" and r["t"] != tsel:
                continue
            with st.expander(f"{TOPIC[r['t']]['emoji']} {r['q']}"):
                st.caption("Try answering out loud first, then compare.")
                st.markdown(r["a"])
                st.caption(f"Source: {r['s']}")
                speak(r["q"] + " Model answer: " + r["a"], f"rv{k}", "🔊 Listen")
    with t3:
        st.markdown("The AS23 sample exam came with an answer key. These items disagree with the course material or couldn't be verified:")
        for q in QUESTIONS:
            if q.get("flag"):
                with st.container(border=True):
                    st.markdown(f"**{q['sample']}: {q['q']}**")
                    st.markdown(f"Key says **{'abc'[q['key']]}** · course material supports **{'abc'[q['a']]}**")
                    st.caption(q["flag"])


{
    "🏠 Home & plan": page_home,
    "🗺️ Quest map": page_quest,
    "⚡ Lightning round": page_lightning,
    "🃏 Flashcards": page_cards,
    "🧩 Sort it": page_sort,
    "🔗 Match-up": page_match,
    "📝 Exam simulator": page_exam,
    "🎯 Mistake review": page_mistakes,
    "🚩 Traps & review questions": page_traps,
}[page]()
