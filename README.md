# Deciora — AI Decision Engine for Career & Research Opportunities

Deciora is an AI-powered decision engine designed to help students and early-career applicants evaluate whether an opportunity is truly worth pursuing.

Instead of optimizing for more applications, Deciora focuses on **better decisions** — helping users determine where to invest their time across both **career opportunities** (jobs, internships) and **research opportunities** (labs, professors, academic projects).

---

## 🚀 Why Deciora exists

Today’s applicants are not short of opportunities — they are overwhelmed by them.

- Job descriptions are often vague, inflated, or inconsistent  
- Platforms show listings, but rarely explain true fit  
- Research opportunities are even harder to evaluate  
- Applicants waste time applying broadly without a clear decision framework  

Deciora is built to solve a simple but critical problem:

> **Not where you can apply — but where you should apply.**

---

## 🧠 Core idea

Deciora is not a resume checker or keyword matcher.

It is a **decision support system** that evaluates opportunities across multiple dimensions and produces a clear, actionable recommendation.

The system combines:

- Resume parsing  
- Opportunity understanding (job + research)  
- Fit evaluation  
- Risk detection  
- Structured recommendation output  

The goal is to help users move from **guessing → evaluating → deciding**.

---

## ⚙️ What the app does

- Extracts opportunity information from a URL (when possible)  
- Falls back to pasted job / research descriptions  
- Parses PDF resumes using PyMuPDF  
- Evaluates fit across:
  - skills  
  - experience  
  - education  
  - keyword alignment  
- Flags potential risk signals (e.g., vague roles, unrealistic requirements)  
- Returns a final recommendation:
  - **Apply**
  - **Reach**
  - **Avoid**
- Runs in deterministic demo mode (no API required)  
- Optionally enhances reasoning with an OpenAI-compatible API  

---

## 🔍 How it works

### 1. Input
- Upload a PDF resume  
- Provide a job URL or research description  

### 2. Extraction
- Parse resume content  
- Extract structured information from the opportunity  

### 3. Matching
- Compare user profile with opportunity requirements  
- Identify alignment, gaps, and signals  

### 4. Decision
- Generate a recommendation  
- Surface risks and trade-offs  
- Help the user decide whether to proceed  

---

## 🆚 Competitive advantages

### 1. Decision-oriented (not just analysis)
Most tools stop at “match scores.”  
Deciora answers a more practical question:

> **Should you pursue this opportunity or not?**

---

### 2. Covers both career and research paths
Unlike traditional tools, Deciora supports:

- internships & jobs  
- research labs & professors  

This makes it more aligned with real student decision flows.

---

### 3. Built for early-career users
Designed specifically for:

- students  
- internship applicants  
- entry-level candidates  
- users exploring research pathways  

---

### 4. Works with messy real-world inputs
- Handles inconsistent job pages  
- Supports fallback to pasted descriptions  
- Designed for real usage, not ideal inputs  

---

### 5. Structured outputs over black-box AI
- Transparent logic  
- Clear reasoning  
- Actionable recommendation  

Not just “AI says yes/no.”

---

## 👤 Who this is for

- Students applying for internships  
- Early-career applicants screening roles  
- Users exploring research opportunities  
- Anyone who wants to filter opportunities before investing time  

---

## 🧱 Tech stack

- **Python 3.12**  
- **Streamlit**  
- **PyMuPDF**  
- **OpenAI-compatible API (optional)**  
- Custom logic for parsing, matching, and decision scoring  

---

## 🧪 Project status

This project is currently in **MVP / demo stage**, with:

- deterministic logic for consistent testing  
- optional LLM enhancement  
- ongoing iteration on decision logic and UX  

---

## 🌱 Vision

Deciora aims to become the **decision layer for early-career opportunities**.

In a world where access is no longer the problem,  
**judgment becomes the bottleneck.**

---

## 🔗 Demo

👉 https://decioraai.streamlit.app/
