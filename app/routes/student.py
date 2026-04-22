from flask import Blueprint, request, jsonify
from flask_login import login_required, current_user
from app import db
from app.models import Submission, SubmissionPage, Test, Evaluation, Question
from app.tasks.ocr_tasks import process_submission
import os
import json

student = Blueprint("student", __name__)

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))

ALLOWED_EXTENSIONS = {'jpg', 'jpeg', 'png', 'pdf'}
MAX_FILE_SIZE_MB = 10

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@student.route("/submit", methods=["POST"])
@login_required
def submit():
    if current_user.role != "student":
        return jsonify({"error": "Only students can submit answers"}), 403

    test_id = request.form.get("test_id")
    if not test_id:
        return jsonify({"error": "test_id is required"}), 400

    # Validate test_id is a number
    try:
        test_id = int(test_id)
    except ValueError:
        return jsonify({"error": "test_id must be a number"}), 400

    # Check test exists
    test = Test.query.get(test_id)
    if not test:
        return jsonify({"error": f"Test {test_id} not found"}), 404

    # Check image uploaded
    if "image" not in request.files:
        return jsonify({"error": "No image file uploaded"}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No file selected"}), 400

    # Validate file type
    if not allowed_file(file.filename):
        return jsonify({"error": f"Invalid file type. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"}), 400

    # Validate file size
    file.seek(0, 2)  # seek to end
    file_size_mb = file.tell() / (1024 * 1024)
    file.seek(0)  # reset
    if file_size_mb > MAX_FILE_SIZE_MB:
        return jsonify({"error": f"File too large. Max size is {MAX_FILE_SIZE_MB}MB"}), 400

    # Check student hasn't already submitted for this test
    existing = Submission.query.filter_by(
        test_id=test_id,
        student_id=current_user.id
    ).first()
    if existing:
        return jsonify({
            "error": "You have already submitted for this test",
            "existing_submission_id": existing.id,
            "status": existing.status
        }), 400

    try:
        # Save uploaded image
        upload_dir = os.path.join(BASE_DIR, "uploads")
        os.makedirs(upload_dir, exist_ok=True)

        # Create submission record
        submission = Submission(
            test_id=test_id,
            student_id=current_user.id,
            status="pending"
        )
        db.session.add(submission)
        db.session.flush()

        filename = f"submission_{submission.id}_page1{os.path.splitext(file.filename)[1]}"
        filepath = os.path.join(upload_dir, filename)
        file.save(filepath)

        # Save submission page
        page = SubmissionPage(
            submission_id=submission.id,
            page_number=1,
            image_path=filepath,
            processed_text=None
        )
        db.session.add(page)
        db.session.commit()

        # Fire Celery task
        try:
            process_submission.delay(submission.id)
        except Exception as celery_error:
            # Celery failed but submission is saved — mark as pending
            print(f"Celery error: {celery_error}")
            return jsonify({
                "message": "Submitted successfully but processing delayed",
                "submission_id": submission.id,
                "status": "pending",
                "warning": "Background processing unavailable, will retry"
            }), 201

        return jsonify({
            "message": "Submitted successfully",
            "submission_id": submission.id,
            "status": "pending"
        }), 201

    except Exception as e:
        db.session.rollback()
        print(f"Submission error: {e}")
        return jsonify({"error": "Failed to save submission. Please try again."}), 500


@student.route("/submission/status/<int:submission_id>", methods=["GET"])
@login_required
def submission_status(submission_id):
    submission = Submission.query.get(submission_id)

    if not submission:
        return jsonify({"error": "Submission not found"}), 404

    if current_user.role == "student" and submission.student_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    return jsonify({
        "submission_id": submission.id,
        "status": submission.status,
        "uploaded_at": submission.uploaded_at.isoformat(),
        "test_id": submission.test_id
    }), 200


@student.route("/results/<int:submission_id>", methods=["GET"])
@login_required
def get_results(submission_id):
    submission = Submission.query.get(submission_id)
    if not submission:
        return jsonify({"error": "Submission not found"}), 404

    if current_user.role == "student" and submission.student_id != current_user.id:
        return jsonify({"error": "Unauthorized"}), 403

    if submission.status != "published":
        return jsonify({
            "error": "Results not yet published",
            "status": submission.status
        }), 403

    evaluations = Evaluation.query.filter_by(submission_id=submission_id).all()

    results = []
    total_scored = 0
    total_max = 0

    for ev in evaluations:
        question = Question.query.get(ev.question_id)
        results.append({
            "question_number": question.question_number,
            "question_text": question.question_text,
            "max_marks": question.max_marks,
            "final_score": ev.final_score,
            "feedback": ev.ai_feedback
        })
        total_scored += ev.final_score or 0
        total_max += question.max_marks

    return jsonify({
        "submission_id": submission_id,
        "test_id": submission.test_id,
        "status": submission.status,
        "total_score": total_scored,
        "total_max_marks": total_max,
        "percentage": round((total_scored / total_max) * 100, 2) if total_max > 0 else 0,
        "results": results
    }), 200