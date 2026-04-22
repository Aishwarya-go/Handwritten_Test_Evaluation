from flask import Blueprint, request, jsonify, send_file
from flask_login import login_required, current_user
from app import db
from app.models import Test, Question
from app.utils.pdf_generator import generate_answer_sheet
from app.models import Test, Question, Submission, Evaluation
import json
import os

teacher = Blueprint("teacher", __name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

@teacher.route("/test/create", methods=["POST"])
@login_required
def create_test():
    if current_user.role != "teacher":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()

    if not data.get("title") or not data.get("questions"):
        return jsonify({"error": "title and questions are required"}), 400

    total_marks = sum(q["max_marks"] for q in data["questions"])

    test = Test(
        teacher_id=current_user.id,
        title=data["title"],
        total_marks=total_marks
    )
    db.session.add(test)
    db.session.flush()

    questions_for_pdf = []
    for q in data["questions"]:
        question = Question(
            test_id=test.id,
            question_number=q["question_number"],
            question_text=q.get("question_text", ""),
            model_answer=q["model_answer"],
            max_marks=q["max_marks"],
            rubric_json=json.dumps(q["rubric"])
        )
        db.session.add(question)
        questions_for_pdf.append({
            "question_number": q["question_number"],
            "question_text": q.get("question_text", f"Question {q['question_number']}"),
            "max_marks": q["max_marks"]
        })

    db.session.flush()

    pdf_path = os.path.join(BASE_DIR, 'generated_pdfs', f'test_{test.id}_answersheet.pdf')
    os.makedirs(os.path.join(BASE_DIR, 'generated_pdfs'), exist_ok=True)

    bounding_boxes = generate_answer_sheet(
        test_id=test.id,
        title=data["title"],
        questions=questions_for_pdf,
        output_path=pdf_path
    )

    for bbox in bounding_boxes:
        q_record = Question.query.filter_by(
            test_id=test.id,
            question_number=bbox["question_number"]
        ).first()
        if q_record:
            q_record.rubric_json = json.dumps({
                "rubric": json.loads(q_record.rubric_json),
                "bbox": bbox
            })

    db.session.commit()

    return jsonify({
        "message": "Test created successfully",
        "test_id": test.id,
        "total_marks": total_marks,
        "pdf_url": f"/test/{test.id}/download-sheet",
        "bounding_boxes": bounding_boxes
    }), 201


@teacher.route("/test/<int:test_id>/download-sheet", methods=["GET"])
@login_required
def download_sheet(test_id):
    pdf_path = os.path.join(BASE_DIR, 'generated_pdfs', f'test_{test_id}_answersheet.pdf')
    if not os.path.exists(pdf_path):
        return jsonify({"error": "PDF not found"}), 404
    return send_file(pdf_path, as_attachment=True,
                     download_name=f"answersheet_test_{test_id}.pdf")

@teacher.route("/queue", methods=["GET"])
@login_required
def get_queue():
    if current_user.role != "teacher":
        return jsonify({"error": "Unauthorized"}), 403

    # Get all submissions for tests owned by this teacher
    from app.models import Submission, User
    submissions = Submission.query\
        .join(Test, Submission.test_id == Test.id)\
        .filter(Test.teacher_id == current_user.id)\
        .all()

    result = []
    for sub in submissions:
        student = User.query.get(sub.student_id)
        result.append({
            "submission_id": sub.id,
            "test_id": sub.test_id,
            "student_name": student.name if student else "Unknown",
            "status": sub.status,
            "uploaded_at": sub.uploaded_at.isoformat()
        })

    return jsonify({"queue": result}), 200

@teacher.route("/review/<int:submission_id>", methods=["GET"])
@login_required
def get_review(submission_id):
    if current_user.role != "teacher":
        return jsonify({"error": "Unauthorized"}), 403

    submission = Submission.query.get(submission_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404

    # Check this submission belongs to teacher's test
    test = Test.query.get(submission.test_id)
    if test.teacher_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    # Get all evaluations for this submission
    evaluations = Evaluation.query.filter_by(submission_id=submission_id).all()

    result = []
    for ev in evaluations:
        question = Question.query.get(ev.question_id)
        import json
        rubric_data = json.loads(question.rubric_json)
        if isinstance(rubric_data, dict) and "rubric" in rubric_data:
            rubric = rubric_data["rubric"]
            bbox = rubric_data.get("bbox", {})
        else:
            rubric = rubric_data
            bbox = {}

        result.append({
            "evaluation_id": ev.id,
            "question_number": question.question_number,
            "question_text": question.question_text,
            "max_marks": question.max_marks,
            "rubric": rubric,
            "extracted_answer": ev.extracted_answer,
            "ai_score": ev.ai_score,
            "ai_feedback": ev.ai_feedback,
            "confidence": ev.confidence,
            "teacher_score": ev.teacher_score,
            "final_score": ev.final_score,
            "ocr_quality_concern": ev.confidence < 0.6 if ev.confidence else False,
            "bbox": bbox
        })

    return jsonify({
        "submission_id": submission_id,
        "status": submission.status,
        "evaluations": result
    }), 200


@teacher.route("/review/save", methods=["POST"])
@login_required
def save_review():
    if current_user.role != "teacher":
        return jsonify({"error": "Unauthorized"}), 403

    data = request.get_json()

    # Validate
    if not data.get("evaluation_id") or data.get("teacher_score") is None:
        return jsonify({"error": "evaluation_id and teacher_score are required"}), 400

    evaluation = Evaluation.query.get(data["evaluation_id"])
    if not evaluation:
        return jsonify({"error": "Evaluation not found"}), 404

    # Verify this evaluation belongs to teacher's test
    submission = Submission.query.get(evaluation.submission_id)
    test = Test.query.get(submission.test_id)
    if test.teacher_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    # Get max marks for validation
    question = Question.query.get(evaluation.question_id)
    teacher_score = float(data["teacher_score"])

    # Clamp score to valid range
    teacher_score = max(0, min(teacher_score, question.max_marks))

    # Save teacher score and update final score
    evaluation.teacher_score = teacher_score
    evaluation.final_score = teacher_score  # teacher override takes priority
    db.session.commit()

    return jsonify({
        "message": "Score saved",
        "evaluation_id": evaluation.id,
        "teacher_score": teacher_score,
        "final_score": teacher_score
    }), 200

@teacher.route("/publish/<int:submission_id>", methods=["POST"])
@login_required
def publish(submission_id):
    if current_user.role != "teacher":
        return jsonify({"error": "Unauthorized"}), 403

    submission = Submission.query.get(submission_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404

    # Verify this submission belongs to teacher's test
    test = Test.query.get(submission.test_id)
    if test.teacher_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    # Check submission is ready to publish
    if submission.status not in ["llm_done", "reviewed"]:
        return jsonify({"error": f"Submission is not ready to publish. Current status: {submission.status}"}), 400

    # Compute final scores — use teacher_score if set, else ai_score
    evaluations = Evaluation.query.filter_by(submission_id=submission_id).all()

    if not evaluations:
        return jsonify({"error": "No evaluations found for this submission"}), 400

    total_final_score = 0
    for ev in evaluations:
        # Teacher score takes priority over AI score
        if ev.teacher_score is not None:
            ev.final_score = ev.teacher_score
        else:
            ev.final_score = ev.ai_score or 0
        total_final_score += ev.final_score

    # Mark submission as published
    submission.status = "published"
    db.session.commit()

    return jsonify({
        "message": "Submission published successfully",
        "submission_id": submission_id,
        "total_final_score": total_final_score,
        "status": "published"
    }), 200