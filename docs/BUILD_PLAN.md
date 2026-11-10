# Build plan: Oct 31 → Nov 10, 2026

The submission deadline (Nov 10) is final. Engagement on your LinkedIn/X post counts toward
shortlisting, so the post goes out **Nov 6** to collect reactions before the cutoff.

| Date | Goal | Done when |
|---|---|---|
| **Sat Oct 31** | Register on the form. Run this repo in mock mode. Push to GitHub. Accept Evon's HF terms, check its architecture. Ask Gnani Discord about hosted Evon. | App runs on your laptop; tests pass |
| Sun Nov 1 | Credits arrive → `MOCK_TTS=0`, then `MOCK_STT=0`. Record 5 clips yourself in Tamil and Hindi. | Real Prisma transcript + real Timbre read-back |
| Mon Nov 2 | Get Evon running (`docs/EVON_HOSTING.md`). `MOCK_LLM=0`. Tune the prompt on your 5 clips. | `engine: evon` on visits; `run_eval.py --text` works |
| Tue Nov 3 | Deploy (Docker on Render/Railway). Test on your phone over https, including airplane mode → record → reconnect → sync. | Works on a real Android phone |
| Wed Nov 4 | **Evaluation day.** `make_test_clips.py` + record 20–30 real clips with friends (fan noise, traffic, kids, Tanglish/Hinglish). If possible: 10 minutes with a nursing student, ANM or ASHA. Fix the top 3 errors. | Real numbers in `eval/report.csv` |
| Thu Nov 5 | Polish. Record the 60-second demo video (script below). | Video exported |
| **Fri Nov 6** | **Post on LinkedIn + X.** Write the project explanation for the submission. | Posts live, tagged correctly |
| Sat–Sun Nov 7–8 | Reply to every comment. Post a follow-up with your accuracy table or a real-user clip. | |
| **Mon Nov 9** | **Submit** (one day early): demo/video, written explanation, Gnani models used, post links. | Confirmation received |
| Tue Nov 10 | Buffer only. | |

## 60-second demo video

| Time | On screen |
|---|---|
| 0–5 s | "India's 10 lakh ASHA workers write every visit twice and lose pay when uploads fail." |
| 5–12 s | Paper register, then a loading spinner on a government app |
| 12–30 s | Tamil voice note → register entry fills in → Timbre reads it back → she says "சரி" → saved |
| 30–40 s | High BP stamp → ANM dashboard row turns red |
| 40–50 s | Switch to Hindi; morning briefing plays: "आज आपकी 6 विज़िट हैं…" |
| 50–60 s | Your accuracy numbers + "Built on Gnani Prisma, Evon and Timbre" |

Post must: show the app working, name the Gnani tech, tag Gnani AI's official account, and include
**#GnaniAI** and **#GreatIndianAIInternshipChallenge**. No bought engagement or engagement swaps.

## Award categories this targets

Regional languages · Hinglish/code-mixed voice · Real-world impact · Best solo/duo project
