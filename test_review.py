import requests, json

s = requests.Session()
s.post('http://127.0.0.1:5000/login', json={'email':'teacher@test.com','password':'pass123'})
r = s.get('http://127.0.0.1:5000/review/3')
data = r.json()
print('Status:', data['status'])
for ev in data['evaluations']:
    print(f"Q{ev['question_number']}: AI Score={ev['ai_score']}, Feedback={ev['ai_feedback']}")