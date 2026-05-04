from app import create_app, db
from app.models import Submission, Evaluation, Question

app = create_app()
with app.app_context():
    s = db.session.get(Submission, 1)
    if not s:
        print("No submission found with id=1")
    else:
        print(f"Submission: id={s.id} status={s.status} test_id={s.test_id}")
        questions = Question.query.filter_by(test_id=s.test_id).all()
        print(f"Questions found: {len(questions)}")

        # delete existing evals first
        Evaluation.query.filter_by(submission_id=s.id).delete()
        db.session.commit()

        for q in questions:
            ev = Evaluation(
                submission_id=s.id,
                question_id=q.id,
                extracted_answer=f"Sample answer for Q{q.question_number}. The student wrote a reasonable response covering the main points.",
                ai_score=round(q.max_marks * 0.8, 1),
                ai_feedback="Good attempt. Key points covered. Could elaborate more on examples.",
                confidence=0.85,
                final_score=round(q.max_marks * 0.8, 1)
            )
            db.session.add(ev)

        db.session.commit()
        count = Evaluation.query.filter_by(submission_id=s.id).count()
        print(f"Evaluations created: {count}")
        print("Now go to Review Queue and click Review -> Publish Results")
