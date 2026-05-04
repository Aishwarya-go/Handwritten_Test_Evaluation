from app.utils.llm_evaluator import evaluate_answer

result = evaluate_answer(
    question_text="What is Newton's Second Law?",
    model_answer="Force equals mass times acceleration. F=ma. SI unit is Newton.",
    rubric=["Mentions F=ma: 2pts", "Explains force and acceleration: 2pts", "States SI unit: 1pt"],
    student_answer="Force equals mass times acceleration which is written as F=ma",
    max_marks=5,
    groq_api_key=""
)
print("Score:", result['score'], "/ 5")
print("Confidence:", result['confidence'])
print("Matched:", result['matched_points'])
print("Missing:", result['missing_points'])
print("Feedback:", result['feedback'])
