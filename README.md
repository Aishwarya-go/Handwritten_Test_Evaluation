# Handwritten Test Evaluation System — Backend

## Setup Instructions

### 1. Clone and install
```bash
git clone <repo-url>
cd Handwritten_Test_Evaluation
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Set up PostgreSQL
- Create database: `CREATE DATABASE testpaper_db;`
- Update `config.py` with your PostgreSQL password

### 3. Install and start Redis (Windows)
- Download Memurai from https://www.memurai.com/
- It starts automatically as a Windows service

### 4. Run the app
Terminal 1 — Flask:
```bash
python run.py
```

Terminal 2 — Celery:
```bash
celery -A app.tasks.ocr_tasks.celery worker --loglevel=info --pool=solo
```

### 5. Seed demo data
```bash
python seed.py
```

### 6. Demo credentials
| Role | Email | Password |
|------|-------|----------|
| Teacher | teacher@demo.com | demo123 |
| Student 1 | alice@demo.com | demo123 |
| Student 2 | bob@demo.com | demo123 |
| Student 3 | charlie@demo.com | demo123 |

## API Routes

| Method | Route | Role | Description |
|--------|-------|------|-------------|
| POST | /register | Any | Register user |
| POST | /login | Any | Login |
| POST | /logout | Any | Logout |
| POST | /test/create | Teacher | Create test + generate PDF |
| GET | /test/<id>/download-sheet | Teacher | Download answer sheet PDF |
| GET | /queue | Teacher | View all submissions |
| GET | /review/<submission_id> | Teacher | View evaluations |
| POST | /review/save | Teacher | Override score |
| POST | /publish/<submission_id> | Teacher | Publish results |
| POST | /submit | Student | Upload answer sheet |
| GET | /submission/status/<id> | Student | Check processing status |
| GET | /results/<submission_id> | Student | View published results |