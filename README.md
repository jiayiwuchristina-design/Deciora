# ApplyPilot — AI Career Decision Engine

ApplyPilot is an AI-powered decision support tool that helps students and early-career applicants decide whether an opportunity is worth applying to.

Instead of manually comparing a resume against a job post, ApplyPilot extracts role information, parses resume content, evaluates fit across multiple dimensions, flags potential risks, and returns a practical recommendation: **Apply**, **Consider**, or **Skip**.

## Why this project exists

Students and early-career applicants often face the same problem:

- job descriptions are long, vague, or inflated
- online platforms show openings, but rarely explain whether a role is actually a good fit
- manually screening each opportunity takes too much time
- many applicants apply too broadly without a clear decision process

ApplyPilot is built to make the first application decision faster, clearer, and more intentional.

## Core idea

ApplyPilot is not just a resume keyword checker.

It is designed as a lightweight decision engine that combines:

- resume parsing
- job description understanding
- fit evaluation
- risk detection
- recommendation output

The goal is simple: help users decide **where to focus their time**, instead of blindly applying everywhere.

## What the app does

- extracts job text from a URL when possible
- falls back to pasted job description text when scraping is unavailable
- parses PDF resumes with PyMuPDF
- evaluates fit across skills, keywords, education, and experience
- flags company or posting risk signals
- returns a final recommendation:
  - **Apply**
  - **Consider**
  - **Skip**
- runs end-to-end in deterministic demo mode without requiring a paid API key
- optionally enhances final reasoning with an OpenAI-compatible API

## How it works

The current MVP follows this workflow:

1. **Input**
   - upload a PDF resume
   - provide a job URL or paste a job description

2. **Extraction**
   - parse resume text
   - extract job information from the page or pasted content

3. **Matching**
   - compare resume and role content
   - identify alignment and gaps across key dimensions

4. **Decision support**
   - generate a recommendation
   - surface risk signals
   - help the user decide whether the opportunity is worth pursuing

## Competitive advantages

### 1. Decision-oriented, not just analysis-oriented
Many tools stop at “match score” or generic resume feedback.  
ApplyPilot is designed to answer a more practical question:

**Should this person apply to this opportunity or not?**

That makes the product more action-focused and more useful in real workflows.

### 2. Built for early-career users
Most hiring tools are either too generic or too enterprise-focused.  
ApplyPilot is specifically designed for:

- students
- internship applicants
- entry-level candidates
- users exploring research or early-career opportunities

### 3. Handles messy real-world inputs
Job pages are often inconsistent.  
ApplyPilot is built with fallback logic, so it can still function when direct job extraction fails by using pasted job description text instead.

### 4. Works without requiring a paid API
The app can run in deterministic demo mode without API credentials, which makes it easier to test, demo, and iterate.

### 5. Structured output over black-box output
The logic is designed to produce a more interpretable recommendation rather than only a vague AI-generated answer.

## Who this is for

ApplyPilot is currently most relevant for:

- students applying for internships
- early-career applicants screening entry-level roles
- users exploring whether a research role, internship, or job is realistically worth pursuing
- anyone who wants faster first-pass filtering before investing time in applications

## Tech stack

- **Python 3.12**
- **Streamlit**
- **PyMuPDF**
- **OpenAI-compatible API** (optional)
- supporting utility modules for parsing, matching, and recommendation logic

## Project structure

```text
.
├── app.py
├── sample_data.py
├── requirements.txt
├── README.md
├── .env.example
├── utils/
├── scripts/
├── tests/
└── pages/
