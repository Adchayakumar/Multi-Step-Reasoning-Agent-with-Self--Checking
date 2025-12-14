# tests.py
import json
from agent import solve  

EASY_QUESTIONS = [
    "A train leaves at 12:30 and arrives at 18:05. How long is the journey?",
    "Alice has 3 red apples and twice as many green apples as red. How many apples does she have in total?",
    "If you have 15 chocolates and give 7 to a friend, how many are left?",
    "A movie starts at 09:45 and ends at 11:10. How long does it last?",
    "Tom has 8 pens and buys 5 more. How many pens does he have now?"
]

TRICKY_QUESTIONS = [
    "Ravi has 20 marbles. He gives 4 to Sita and 3 to Arjun, then buys 5 more. How many marbles does he have now?",
    "A shop sells boxes with 6 or 8 cookies each. Rohan buys 3 boxes and gets 22 cookies in total. How many boxes of each type might he have bought?",
    "A meeting needs exactly 30 minutes. Free slots are 10:00–10:30, 10:30–11:00, 10:45–11:15. Which slots can fit the meeting?"
]

def run_tests(questions, label):
    print(f"\n=== {label} TESTS ===")
    for i, q in enumerate(questions, start=1):
        print(f"\n--- Test {i} ---")
        print(f"Question: {q}")
        result = solve(q, max_retries=1)
        print("Final JSON:")
        print(json.dumps(result, indent=2))

        # Derive the required logs from result
        status = result.get("status")
        checks = result.get("metadata", {}).get("checks", [])
        retries = result.get("metadata", {}).get("retries", 0)

        verifier_passed = all(c.get("passed", False) for c in checks) if checks else (status == "success")

        print(f"Verifier passed: {verifier_passed}")
        print(f"Agent retries: {retries}")

if __name__ == "__main__":
    run_tests(EASY_QUESTIONS, "EASY")
    run_tests(TRICKY_QUESTIONS, "TRICKY")
