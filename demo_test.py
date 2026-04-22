import requests
import time
import json

BASE = "http://127.0.0.1:5000"

def test(name, condition, response=None):
    if condition:
        print(f"  ✅ {name}")
    else:
        print(f"  ❌ {name}")
        if response:
            print(f"     Response: {response.text[:200]}")

print("=" * 50)
print("FULL DEMO TEST")
print("=" * 50)

# ── Teacher session ──
print("\n[1] Teacher Login")
teacher = requests.Session()
r = teacher.post(f"{BASE}/login", json={"email": "teacher@demo.com", "password": "demo123"})
test("Teacher login", r.status_code == 200, r)

# ── Create test ──
print("\n[2] Create Test")
r = teacher.post(f"{BASE}/test/create", json={
    "title": "Demo Physics Test",
    "questions": [
        {
            "question_number": 1,
            "question_text": "What is Newton's Second Law?",
            "model_answer": "F=ma. Force equals mass times acceleration.",
            "max_marks": 5,
            "rubric": ["Mentions F=ma: 2pts", "Explains relationship: 2pts", "Correct units: 1pt"]
        },
        {
            "question_number": 2,
            "question_text": "Define velocity.",
            "model_answer": "Rate of change of displacement. Vector quantity.",
            "max_marks": 3,
            "rubric": ["Correct definition: 2pts", "Mentions vector: 1pt"]
        }
    ]
})
test("Test created", r.status_code == 201, r)
test_id = r.json().get("test_id")
print(f"     Test ID: {test_id}")

# ── Download PDF ──
print("\n[3] Download Answer Sheet PDF")
r = teacher.get(f"{BASE}/test/{test_id}/download-sheet")
test("PDF downloaded", r.status_code == 200, r)

# ── Student submits ──
print("\n[4] Student Submission")
alice = requests.Session()
r = alice.post(f"{BASE}/login", json={"email": "alice@demo.com", "password": "demo123"})
test("Alice login", r.status_code == 200, r)

r = alice.post(f"{BASE}/submit",
    data={"test_id": str(test_id)},
    files={"image": open("answersheet.pdf", "rb")}
)
test("Alice submission accepted", r.status_code == 201, r)
submission_id = r.json().get("submission_id")
print(f"     Submission ID: {submission_id}")

# ── Wait for pipeline ──
print("\n[5] Waiting for OCR + LLM pipeline (8 seconds)...")
time.sleep(8)

r = alice.get(f"{BASE}/submission/status/{submission_id}")
status = r.json().get("status")
test(f"Pipeline completed (status={status})", status == "llm_done", r)

# ── Teacher reviews ──
print("\n[6] Teacher Review")
r = teacher.get(f"{BASE}/review/{submission_id}")
test("Review page loads", r.status_code == 200, r)
evaluations = r.json().get("evaluations", [])
test(f"Evaluations returned ({len(evaluations)} questions)", len(evaluations) > 0)

# Print scores
for ev in evaluations:
    print(f"     Q{ev['question_number']}: AI Score = {ev['ai_score']}/{ev['max_marks']}")

# Override Q1 score
eval_id = evaluations[0]["evaluation_id"] if evaluations else None
if eval_id:
    r = teacher.post(f"{BASE}/review/save", json={"evaluation_id": eval_id, "teacher_score": 4})
    test("Teacher score override saved", r.status_code == 200, r)

# ── Teacher publishes ──
print("\n[7] Publish Results")
r = teacher.post(f"{BASE}/publish/{submission_id}")
test("Results published", r.status_code == 200, r)
total = r.json().get("total_final_score")
print(f"     Total Score: {total}")

# ── Student views results ──
print("\n[8] Student Views Results")
r = alice.get(f"{BASE}/results/{submission_id}")
test("Results visible to student", r.status_code == 200, r)
data = r.json()
print(f"     Score: {data.get('total_score')}/{data.get('total_max_marks')} ({data.get('percentage')}%)")

# ── Error handling ──
print("\n[9] Error Handling")
with open("test.txt", "w") as f:
    f.write("not an image")
r = alice.post(f"{BASE}/submit", data={"test_id": str(test_id)},
    files={"image": open("test.txt", "rb")})
test("Duplicate submission blocked", "already submitted" in r.text or "Invalid" in r.text)

# ── Teacher queue ──
print("\n[10] Teacher Queue")
r = teacher.get(f"{BASE}/queue")
test("Queue loads", r.status_code == 200, r)
queue = r.json().get("queue", [])
print(f"     Total submissions in queue: {len(queue)}")

print()
print("=" * 50)
print("DEMO TEST COMPLETE")
print("=" * 50)