import requests

s = requests.Session()
s.post('http://127.0.0.1:5000/login', json={'email':'student@test.com','password':'pass123'})
r = s.get('http://127.0.0.1:5000/results/3')
data = r.json()

print(f"Total Score: {data['total_score']} / {data['total_max_marks']}")
print(f"Percentage: {data['percentage']}%")
print()
for q in data['results']:
    print(f"Q{q['question_number']}: {q['final_score']}/{q['max_marks']}")
    print(f"Feedback: {q['feedback']}")
    print()