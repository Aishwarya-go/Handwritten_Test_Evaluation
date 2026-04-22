from app import create_app, db
from app.models import User, Test, Question
from werkzeug.security import generate_password_hash
import json

app = create_app()

def seed():
    with app.app_context():
        print("Seeding demo data...")

        # Clear existing demo data
        print("Clearing old data...")
        db.session.execute(db.text("DELETE FROM evaluations"))
        db.session.execute(db.text("DELETE FROM submission_pages"))
        db.session.execute(db.text("DELETE FROM submissions"))
        db.session.execute(db.text("DELETE FROM questions"))
        db.session.execute(db.text("DELETE FROM tests"))
        db.session.execute(db.text("DELETE FROM users"))
        db.session.commit()

        # Create 1 teacher
        teacher = User(
            name="Dr. Smith",
            email="teacher@demo.com",
            password_hash=generate_password_hash("demo123"),
            role="teacher"
        )
        db.session.add(teacher)
        db.session.flush()
        print(f"Created teacher: teacher@demo.com / demo123")

        # Create 3 students
        students = [
            User(name="Alice", email="alice@demo.com", password_hash=generate_password_hash("demo123"), role="student"),
            User(name="Bob", email="bob@demo.com", password_hash=generate_password_hash("demo123"), role="student"),
            User(name="Charlie", email="charlie@demo.com", password_hash=generate_password_hash("demo123"), role="student"),
        ]
        for s in students:
            db.session.add(s)
        db.session.flush()
        print("Created 3 students: alice@demo.com, bob@demo.com, charlie@demo.com / demo123")

        # Create 1 test
        test = Test(
            teacher_id=teacher.id,
            title="Physics Unit 1 Test",
            total_marks=20
        )
        db.session.add(test)
        db.session.flush()
        print(f"Created test: Physics Unit 1 Test (ID: {test.id})")

        # Create 4 questions
        questions_data = [
            {
                "number": 1,
                "text": "What is Newton's Second Law of Motion?",
                "answer": "Force equals mass times acceleration (F=ma). The SI unit of force is Newton.",
                "marks": 5,
                "rubric": ["Mentions F=ma: 2pts", "Explains force and acceleration relationship: 2pts", "States correct SI unit: 1pt"]
            },
            {
                "number": 2,
                "text": "Define velocity and distinguish it from speed.",
                "answer": "Velocity is the rate of change of displacement. Unlike speed, velocity is a vector quantity with both magnitude and direction.",
                "marks": 5,
                "rubric": ["Correct definition of velocity: 2pts", "Mentions vector vs scalar: 2pts", "Gives example: 1pt"]
            },
            {
                "number": 3,
                "text": "State the law of conservation of energy.",
                "answer": "Energy cannot be created or destroyed, only transformed from one form to another. The total energy of an isolated system remains constant.",
                "marks": 5,
                "rubric": ["States energy cannot be created/destroyed: 2pts", "Mentions transformation: 2pts", "Mentions isolated system: 1pt"]
            },
            {
                "number": 4,
                "text": "What is the difference between mass and weight?",
                "answer": "Mass is the amount of matter in an object measured in kg. Weight is the gravitational force on an object measured in Newtons. Weight = mass x gravity.",
                "marks": 5,
                "rubric": ["Correct definition of mass: 1pt", "Correct definition of weight: 1pt", "States correct units for each: 2pts", "Gives formula W=mg: 1pt"]
            }
        ]

        for q in questions_data:
            question = Question(
                test_id=test.id,
                question_number=q["number"],
                question_text=q["text"],
                model_answer=q["answer"],
                max_marks=q["marks"],
                rubric_json=json.dumps(q["rubric"])
            )
            db.session.add(question)

        db.session.commit()
        print("Created 4 questions")

        print()
        print("=" * 40)
        print("DEMO CREDENTIALS")
        print("=" * 40)
        print("Teacher:  teacher@demo.com / demo123")
        print("Student1: alice@demo.com   / demo123")
        print("Student2: bob@demo.com     / demo123")
        print("Student3: charlie@demo.com / demo123")
        print(f"Test ID:  {test.id}")
        print("=" * 40)

if __name__ == "__main__":
    seed()