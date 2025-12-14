import os
import json
from typing import Dict, Any

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ---------- GEMINI CONFIG ----------

# Set your API key via environment variable: GEMINI_API_KEY
genai.configure(api_key=os.environ["GEMINI_API_KEY"])
MODEL_NAME = "gemini-2.0-flash"  # change if you want another model


def gemini_call(prompt: str) -> str:
    """Simple wrapper that sends a text prompt to Gemini and returns the text response."""
    model = genai.GenerativeModel(MODEL_NAME)
    resp = model.generate_content(prompt)
    return resp.text or ""


# ---------- PLANNER ----------

def plan(question: str) -> str:
    prompt = f"""
[PLANNER]
You are a planner for small math and logic word problems.

Task:
- Read the QUESTION.
- Produce a short numbered plan with 3–6 steps to solve it.
- Focus on extracting quantities, understanding relationships, computing,
  checking constraints (like non-negative counts, correct time ranges),
  and formatting the final answer.

Output format:
- Only the numbered plan as plain text, e.g.
  1. ...
  2. ...
  3. ...

QUESTION: {question}
"""
    return gemini_call(prompt).strip()


# ---------- EXECUTOR (LLM) ----------

def execute(question: str, plan_text: str) -> Dict[str, Any]:
    prompt = f"""
[EXECUTOR]
You are an executor for math and logic word problems.

You will be given:
- QUESTION: the user's problem.
- PLAN: a numbered plan of steps to solve it.

Task:
- Follow the PLAN step-by-step.
- Do the necessary calculations.
- Keep track of intermediate values.
- Produce a proposed final answer and a short explanation.

IMPORTANT:
- Return ONLY valid JSON.
- Do NOT include any markdown fences or extra text.

JSON schema to return:
{{
  "proposed_answer": "<short final answer as a string>",
  "explanation": "<short explanation including key intermediate steps>",
  "intermediate": {{
    "notes": "<optional free-form notes or parsed info>"
  }}
}}

QUESTION: {question}

PLAN:
{plan_text}
"""
    raw = gemini_call(prompt).strip()

    raw = raw.replace("```json", "").replace("```", "")
    return json.loads(raw)


# ---------- VERIFIER (LLM-ONLY) ----------

def verify_llm(question: str, exec_result: Dict[str, Any]) -> Dict[str, Any]:
    proposed_answer = exec_result.get("proposed_answer", "")
    explanation = exec_result.get("explanation", "")

    prompt = f"""
[VERIFIER]
You are a strict verifier for math and logic word problems.

You will be given:
- QUESTION: the original problem.
- PROPOSED_ANSWER: the answer string.
- EXPLANATION: a short explanation with intermediate reasoning.

Your job:
- Check if the explanation actually solves the QUESTION.
- Check if the arithmetic and logical steps are correct.
- Check if constraints (time ranges, non-negative counts, totals) are satisfied.
- Decide whether the solution is acceptable.

VERY IMPORTANT:
- Return exactly ONE JSON object.
- Do NOT repeat any part of the JSON.
- Do NOT repeat checks.
- Do NOT add any text before or after the JSON.
- Do NOT include markdown like ```json ... ```.

Output:
Return ONLY valid JSON with this schema:
{{
  "passed": true or false,
  "checks": [
    {{
      "check_name": "<short name of this check>",
      "passed": true or false,
      "details": "<one-line description>"
    }}
  ],
  "issues": "<short description of problems if any, empty string if none>"
}}

QUESTION: {question}
PROPOSED_ANSWER: {proposed_answer}
EXPLANATION: {explanation}
"""
    raw = gemini_call(prompt).strip()
    raw = raw.replace("```json", "").replace("```", "")
    return json.loads(raw)


# ---------- SHORT USER-FACING REASONING ----------

def summarize_short(exec_result: Dict[str, Any]) -> str:
    """Create a short explanation suitable for the user."""
    expl = exec_result.get("explanation", "").strip()
    # keep it short to avoid leaking long chain-of-thought
    return expl[:250]


# ---------- MAIN AGENT LOOP ----------

def solve(question: str, max_retries: int = 1) -> Dict[str, Any]:
    """
    Main entry point.

    Returns JSON with schema:
    {
      "answer": "<final short answer>",
      "status": "success" | "failed",
      "reasoning_visible_to_user": "<short explanation>",
      "metadata": {
        "plan": "<internal plan>",
        "checks": [
          { "check_name": "...", "passed": true/false, "details": "..." }
        ],
        "retries": <integer>
      }
    }
    """
    metadata = {"plan": None, "checks": [], "retries": 0}

    for attempt in range(max_retries + 1):
        metadata["retries"] = attempt

        # 1) Plan
        plan_text = plan(question)
        metadata["plan"] = plan_text

        # 2) Execute
        exec_result = execute(question, plan_text)

        # 3) Verify with LLM
        verify_result = verify_llm(question, exec_result)
        metadata["checks"].extend(verify_result.get("checks", []))
        passed = verify_result.get("passed", False)

        if passed:
            return {
                "answer": exec_result.get("proposed_answer", ""),
                "status": "success",
                "reasoning_visible_to_user": summarize_short(exec_result),
                "metadata": metadata,
            }

    # If all retries fail
    return {
        "answer": "",
        "status": "failed",
        "reasoning_visible_to_user": "The agent could not find a consistent solution after verification.",
        "metadata": metadata,
    }


# ---------- CLI ENTRY POINT ----------

if __name__ == "__main__":
    q = input("Enter your question: ")
    result = solve(q, max_retries=1)
    print(json.dumps(result, indent=2))
