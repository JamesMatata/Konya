# Konya — 3.5-Minute Pitch Video Script

**Target length:** 3:00–3:30 (max 3:30)  
**Format:** Quick animation → fast demo → short responsible AI close  
**Voice:** Always **we / our** — never “I”  
**Hackathon:** USAII Hackathon 2026 · Direction A (Benefits Navigator)

---

## Structure at a glance

| Section | Time | Format |
|--------|------|--------|
| **1. Problem & user** | 0:00–0:40 | Animation |
| **2. How our AI works** | 0:40–1:35 | Animation (pipeline) |
| **3. App walkthrough** | 1:35–2:45 | Screen recording |
| **4. Responsible AI** | 2:45–3:20 | Animation + 1 UI shot |
| **Close** | 3:20–3:30 | Logo card |

---

## Opening (0:00–0:06) — No VO

**Visual:** Konya logo → title: *Bring Your Own Policy Navigator*  
**Music:** Low, professional bed starts

---

## Section 1 — Problem & user (0:06–0:40)

### Animation (30 sec)

1. Dense policy page with confusing criteria — age limits, enrollment, income (5 sec). Label flash: *food assistance*, *student aid*
2. Three users flash: someone checking **food assistance**, a **student** reading grant rules, a **parent** on a childcare subsidy page (8 sec)
3. Generic program **directory/list** crossed out → user uploads **their** policy → Konya asks guided questions → **BYOP** label (12 sec)

### Voiceover

> Public support programs — food assistance, student aid, childcare subsidies — come with strict eligibility rules. Most people struggle to tell whether they may qualify, and what steps to take next.
>
> **Konya is not a program directory.** We built it to help users interpret the rules in a policy they already found: translate criteria into plain language, ask relevant questions about their situation — age, enrollment, employment — and guide them toward clear next steps.
>
> They bring the official source. We navigate it with them — in **English, Kiswahili, or Sheng**.

---

## Section 2 — How our AI works (0:40–1:35)

### Animation (55 sec) — One pipeline, four beats

```
Policy in → Gatekeeper → Planner → Interview + Extract → Action Blueprint
```

| Beat | Time | On screen | Voiceover |
|------|------|-----------|-----------|
| **Gatekeeper** | 0:40–0:52 | Shield: relevant? ✅/❌ | First, our **Gatekeeper** checks if the document fits the user’s situation — relevance only, not the final outcome. |
| **Planner** | 0:52–1:04 | Policy → checklist | The **Planner** turns policy rules into a checklist we track internally. |
| **Interview loop** | 1:04–1:22 | Chat + checklist updating; informal answer resolves multiple items | Our **Interviewer** asks focused questions. The **Extractor** parses natural answers — even partial ones — into that checklist. |
| **Blueprint** | 1:22–1:35 | Action Blueprint + “How we reached this” | When done, the **Guide Generator** delivers an **Action Blueprint** — conclusion, what to prepare, and next steps. |

**Skip in animation (save time):** dependency logic, resubmit flow, follow-up mode — mention only in demo or responsible AI if needed.

---

## Section 3 — App walkthrough (1:35–2:45)

**70 seconds.** One continuous screen recording, no detours.

| Time | Show | Voiceover |
|------|------|-----------|
| **1:35–1:45** | Onboarding → guest → Launchpad | We onboard the user, then they describe their situation and add their policy link or file. |
| **1:45–2:00** | Submit → Gatekeeper accepts → chat starts | Once the document is verified, navigation begins. |
| **2:00–2:25** | Answer naturally (e.g. student, 22, no team) → progress bar updates | Users answer in plain language. Our progress strip shows what’s confirmed — without repeating resolved questions. |
| **2:25–2:40** | Action Blueprint → scroll Conclusion / Next Steps | They receive a structured blueprint with clear next steps. |
| **2:40–2:45** | Tap **“How we reached this”** (2 sec) | And they can see how we reached that conclusion. |

### Demo prep checklist

- [ ] Fresh guest session or clean account
- [ ] Policy URL/document ready (USAII or test policy)
- [ ] API key working (`.env`)
- [ ] Browser 100% zoom, hide bookmarks bar
- [ ] Rehearse once; pre-type demo answer if needed

**Sample demo answer (paste or type naturally):**

> I am a student at Multimedia University of Kenya. I am 22 years old, not employed, and for now I don't have a team.

---

## Section 4 — Responsible AI (2:45–3:20)

### Animation (25 sec) — Four icons, fast

1. **BYOP grounding** — answers only from user’s document
2. **Human-in-the-loop** — user confirms facts
3. **Limited scope** — guide, not adjudicator
4. **Transparency** — blueprint + reasoning disclosure

### Voiceover

> We built this responsibly: BYOP grounding, human confirmation, limited scope, and transparency. Konya guides — it does not decide.

---

## Close (3:20–3:30)

**Visual:** Logo + tagline  
**Voiceover (optional, over logo):**

> **Konya. Navigate with clarity.**

Music fade out.

---

## Full voiceover — single narrator (~420 words, ~2:50 read time)

Read this for one continuous VO track; demo section VO can be recorded separately and synced over the screen recording.

> Public support programs — food assistance, student aid, childcare subsidies — come with strict eligibility rules. Most people struggle to tell whether they may qualify, and what steps to take next.
>
> Konya is not a program directory. We built it to interpret rules from a policy the user already found, translate criteria into plain language, ask relevant questions about their situation, and guide them toward clear next steps — in English, Kiswahili, or Sheng.
>
> Konya is a phased AI pipeline, not one generic chatbot. Our Gatekeeper checks document relevance. Our Planner extracts eligibility criteria. Our Interviewer asks focused questions while the Extractor parses natural answers into a checklist. Then our Guide Generator produces an Action Blueprint — conclusion, preparation list, and next steps.
>
> In the app, users describe their situation on the Launchpad, submit their policy, and answer clarifying questions in plain language. Our progress panel tracks what’s confirmed. At the end, they get a structured blueprint — and can expand how we reached that conclusion.
>
> We built this responsibly: BYOP grounding, human confirmation, limited scope, and transparency. Konya guides — it does not decide.
>
> Konya. Navigate with clarity.

---

## Team split (3–4 people)

| Person | Part | ~Time |
|--------|------|-------|
| **A** | Problem + open | 40 sec |
| **B** | AI pipeline animation | 55 sec |
| **C** | Demo (live or VO over recording) | 70 sec |
| **D** | Responsible AI + close | 35 sec |

Each speaker still uses **“we built”**, **“our system”** — never “I built.”

---

## Production notes

### Animation style

- **Colors:** `#0F172A` navy, `#F8FAFC` background, `#2563EB` accent
- **Fonts:** Lora (headings) + Inter (body) — match the app
- **Motion:** 0.4–0.6s ease; clean, professional (no cartoon bounce)

### Recording the demo

- **1080p**, 30fps export
- Slow, deliberate mouse movement
- OBS or Loom; 2–3 rehearsals before final take

### Audio

- Quiet room, light noise reduction
- Music bed at **–18 to –22 dB** under voice

---

## What we cut (from a 5-minute version)

- Long user persona stories
- Dependency logic animation (team / no-team)
- Resubmit / error recovery B-roll
- Follow-up Q&A in demo (unless you have 10 sec spare)
- Long guardrail list — four pillars only

This keeps all four required rubric items inside **3.5 minutes**:

1. Problem and user  
2. How your AI works  
3. Live or recorded walkthrough  
4. Responsible AI choices  
