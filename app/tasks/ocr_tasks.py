from celery import Celery
from celery.utils.log import get_task_logger
import sys
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from app import create_app, db
from app.models import Submission, SubmissionPage, Question, Evaluation

logger = get_task_logger(__name__)

def make_celery():
    return Celery(
        "tasks",
        broker="redis://localhost:6379/0",
        backend="redis://localhost:6379/0"
    )

celery = make_celery()

@celery.task(bind=True, max_retries=3, default_retry_delay=10)
def process_submission(self, submission_id):
    """
    Full pipeline with error handling and retry.
    max_retries=3 means it will retry up to 3 times if it fails.
    default_retry_delay=10 means wait 10 seconds between retries.
    """
    app = create_app()
    with app.app_context():
        submission = Submission.query.get(submission_id)
        if not submission:
            logger.error(f"Submission {submission_id} not found")
            return {"error": "Submission not found"}

        try:
            submission.status = "processing"
            db.session.commit()

            # Mock OCR — ML person replaces with real TrOCR
            mock_ocr_answers = {
                1: "Force equals mass times acceleration. F=ma. SI unit is Newton.",
                2: "Velocity is the rate of change of displacement with time."
            }

            from app.utils.llm_evaluator import evaluate_answer
            from config import Config
            import json

            questions = Question.query.filter_by(
                test_id=submission.test_id
            ).all()

            if not questions:
                raise ValueError(f"No questions found for test {submission.test_id}")

            for question in questions:
                rubric_data = json.loads(question.rubric_json)
                if isinstance(rubric_data, dict) and "rubric" in rubric_data:
                    rubric = rubric_data["rubric"]
                else:
                    rubric = rubric_data

                student_answer = mock_ocr_answers.get(
                    question.question_number,
                    "No answer provided"
                )

                # LLM call with error handling
                try:
                    result = evaluate_answer(
                        question_text=question.question_text or f"Question {question.question_number}",
                        model_answer=question.model_answer,
                        rubric=rubric,
                        student_answer=student_answer,
                        max_marks=question.max_marks,
                        groq_api_key=Config.GROQ_API_KEY
                    )
                except Exception as llm_error:
                    logger.warning(f"LLM error for Q{question.question_number}: {llm_error}, using fallback")
                    result = {
                        "score": 0,
                        "confidence": 0,
                        "matched_points": [],
                        "missing_points": [],
                        "feedback": "Evaluation failed. Teacher review required.",
                        "ocr_quality_concern": True
                    }

                existing = Evaluation.query.filter_by(
                    submission_id=submission_id,
                    question_id=question.id
                ).first()

                if existing:
                    existing.extracted_answer = student_answer
                    existing.ai_score = result["score"]
                    existing.ai_feedback = result["feedback"]
                    existing.confidence = result["confidence"]
                    existing.final_score = result["score"]
                else:
                    evaluation = Evaluation(
                        submission_id=submission_id,
                        question_id=question.id,
                        extracted_answer=student_answer,
                        ai_score=result["score"],
                        ai_feedback=result["feedback"],
                        confidence=result["confidence"],
                        final_score=result["score"]
                    )
                    db.session.add(evaluation)

            db.session.commit()
            submission.status = "llm_done"
            db.session.commit()

            logger.info(f"Submission {submission_id} processed successfully")
            return {"submission_id": submission_id, "status": "llm_done"}

        except Exception as e:
            logger.error(f"Pipeline error for submission {submission_id}: {e}")
            try:
                # Retry the task
                raise self.retry(exc=e)
            except self.MaxRetriesExceededError:
                # All retries failed — mark as failed
                submission.status = "failed"
                db.session.commit()
                return {"error": str(e), "status": "failed"}