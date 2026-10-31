# 🎓 IMBE Exam Quest

A Streamlit learning game for the **International Management & Business Ethics (IMBE)** exam, BSc International Business, Bern University of Applied Sciences (BFH).

## Modes

| Mode | What you do |
|---|---|
| 🏠 Home & plan | Countdown, XP and level, topic mastery table, 5-day study plan checklist |
| 🗺️ Quest map | 13 topics with key points, diagrams and a 🔊 audio lesson, plus a 5-question **boss battle** per topic |
| ⚡ Lightning round | 10 rapid questions with streak multipliers and speed bonuses |
| 🃏 Flashcards | 71 cards with Leitner boxes (again, almost, got it) and read-aloud |
| 🧩 Sort it | Classify items, e.g. reactive vs proactive, compliance vs integrity, Hofstede vs Trompenaars vs Hall |
| 🔗 Match-up | Match terms to definitions or thinkers |
| 📝 Exam simulator | The AS23 sample exam (29 questions) or a random 30-question mock, timed, with per-topic results |
| 🎯 Mistake review | Every question you last answered wrongly, until you clear it |
| 🚩 Traps & review | Exam traps, 31 review questions with model answers, answer-key checks |

**177 questions** in total: the AS23 sample questions plus new ones covering business ethics (responsibility, Kohlberg, utilitarian, deontological and virtue ethics, Paine) and international management (going international and risk, Trompenaars/Hofstede/Hall/GLOBE, culture and corruption, favors in the BRICs (McCarthy et al. 2012), the GBS offshoring-to-India case, China, Lardy, the Social Credit System, the Weichselbaumer study).

Audio uses the browser's built-in text-to-speech (works in Chrome, Edge and Safari). Progress lives in the browser session; use **💾 Save progress** in the sidebar to download it and load it again later.

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Sign in at [share.streamlit.io](https://share.streamlit.io) with GitHub.
2. **Create app → Deploy a public app from GitHub**: repository `humanismContributor/imbe-exam-quest`, branch `main`, main file `app.py`.
3. Click **Deploy**.

## Content

All content lives in `data/` as JSON (`topics.json`, `questions.json`, `extras.json`). The texts are my own study summaries and practice questions based on the course materials; no course PDFs are included. Where the AS23 sample answer key disagrees with the lecture slides or readings, the question carries a 🚩 note explaining why.
