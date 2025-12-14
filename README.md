# Multi‑Step Reasoning Agent with Self‑Checking

This project implements a small multi‑step reasoning agent that solves math/logic word problems using a **Planner → Executor → Verifier** loop on top of an LLM (Gemini). The agent produces a structured JSON response, hides long chain‑of‑thought from the user, and logs internal plans and checks for evaluation.

***

## 1. Project Overview

The agent:

- Takes a plain‑text word problem as input.  
- Internally runs three phases:  
  - **Planner** – designs a step‑by‑step plan to solve the problem.  
  - **Executor** – follows the plan using the LLM to compute a proposed answer and explanation.  
  - **Verifier** – re‑checks the proposed solution using the LLM and returns pass/fail checks.  
- Optionally retries the whole loop a limited number of times if verification fails.  
- Returns a JSON answer with:  
  - `answer`: final short answer.  
  - `status`: `"success"` or `"failed"`.  
  - `reasoning_visible_to_user`: short explanation (no raw chain‑of‑thought).  
  - `metadata`: internal plan, checks, and retry count.

***

## 2. JSON Output Schema

The main entrypoint is `solve(question: str, max_retries: int = 1) -> dict`.

It returns:

```json
{
  "answer": "<final short answer, user-facing>",
  "status": "success" | "failed",
  "reasoning_visible_to_user": "<short explanation>",
  "metadata": {
    "plan": "<planner's internal plan text>",
    "checks": [
      {
        "check_name": "<string>",
        "passed": true,
        "details": "<string>"
      }
    ],
    "retries": 0
  }
}
```

This matches the schema specified in the assignment document.

***

## 3. Architecture and Agent Loop

### Components

- `plan(question: str) -> str`  
  - Calls the LLM with a planner prompt.  
  - Produces a short numbered plan (3–6 steps) describing how to solve the problem (extract quantities, compute, check constraints, format answer).

- `execute(question: str, plan_text: str) -> dict`  
  - Calls the LLM with an executor prompt that includes the question and the plan.  
  - LLM returns JSON text with:
    - `proposed_answer`
    - `explanation`
    - `intermediate` (optional notes/values)  
  - Python uses `json.loads` to convert this string into a dict.

- `verify_llm(question: str, exec_result: dict) -> dict`  
  - Calls the LLM with a verifier prompt containing the question, proposed answer, and explanation.  
  - LLM returns JSON with:
    - `passed`: boolean  
    - `checks`: list of check objects (name, passed, details)  
    - `issues`: short string if something is wrong.

- `summarize_short(exec_result: dict) -> str`  
  - Trims the internal explanation to a short user‑facing message to avoid exposing the full chain‑of‑thought.

- `solve(question: str, max_retries: int = 1) -> dict`  
  - Orchestrates Planner → Executor → Verifier in a loop:
    - `plan(question)`
    - `execute(question, plan_text)`
    - `verify_llm(question, exec_result)`  
  - Appends verifier checks to `metadata["checks"]` and updates `metadata["retries"]`.  
  - If verification passes, returns a `"success"` JSON with answer and short reasoning.  
  - If all attempts fail, returns `"failed"` with explanation.

***

## 4. Tech Stack

- **Language:** Python 3.10+  
- **LLM Provider:**
  - Gemini via `google-generativeai` SDK,
- **Interface:**
  - CLI (`python agent.py`): prompts for a question and prints the JSON.  
  - Core API: `solve(question: str, max_retries: int = 1) -> dict` callable from other scripts or notebooks.

LLM parameters (e.g. `temperature`, `max_output_tokens`) can be adjusted in the LLM client wrapper to trade off determinism vs creativity; for this assignment, a relatively low temperature is used to improve consistency of reasoning and JSON formatting.

***

## 5. Setup and How to Run

### 5.1 Install dependencies

```bash
pip install google-generativeai  
```

### 5.2 Configure API key

For Gemini (example):

```bash
$env:GEMINI_API_KEY="YOUR_GEMINI_API_KEY"        # Windows PowerShell
```

### 5.3 Run interactively (CLI)

```bash
python agent.py
```

Then enter a question, e.g.:

```text
A train leaves at 12:30 and arrives at 18:05. How long is the journey?
```

You will see a JSON printed that matches the schema above, with `status`, `answer`, `reasoning_visible_to_user`, and `metadata`.

***

## 6. Evaluation & Test Cases

A simple test harness is provided in `tests.py`.

### 6.1 Test questions

The test suite includes:

- **Easy questions (5–10):**
  - Basic arithmetic (addition, subtraction).
  - Simple time differences (start time, end time → duration).

- **Tricky questions (3–5):**
  - Multi‑step calculations (several give/take/buy steps).
  - Ambiguous numbers (multiple possible combinations).
  - Edge time/boundary cases (meetings that exactly fit or overlap slots).

The full list of questions used in the tests is available here: [questions.txt](logs/questions.txt)

### 6.2 What each test logs

For each question, `tests.py`:

- Prints the question.  
- Prints the final JSON from `solve(question)`.  
- Computes and logs whether the verifier passed (based on the `checks` list and/or `status`).  
- Logs how many times the agent retried (`metadata["retries"]`).

### 6.3 How to run tests

```bash
python tests.py
```

To persist logs to a file (for submission):

```bash
mkdir -p logs
python tests.py > logs/test_run_1.txt
```

Test run report: [logs/test_run_1.txt](logs/test_run_1.txt)

***

## 7. Prompt Design Notes

Prompts are separated by phase:

- **Planner prompt**
  - Role: “You are a planner for math/logic word problems.”
  - Output: short numbered plan (3–6 steps).
  - Emphasises extracting quantities, computing, checking constraints, and formatting.

- **Executor prompt**
  - Role: “You are an executor; follow the given plan exactly.”
  - Input: question + plan.
  - Output: strictly formatted JSON with `proposed_answer`, `explanation`, `intermediate`.
  - Explicitly instructs model to return only valid JSON, no markdown fences.

- **Verifier prompt**
  - Role: “You are a strict verifier.”
  - Input: question + proposed answer + explanation.
  - Output: JSON with `passed`, `checks`, `issues`.
  - Checks logical consistency, arithmetic, and simple constraints (e.g. non‑negative counts, time ordering).

With more time, the prompts could be improved by:

- Adding more few‑shot examples for tricky edge cases.  
- Making output schemas even more constrained using JSON schema or function calling.
