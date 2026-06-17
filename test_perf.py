import requests
import time

questions = [
    "Qu'est ce que l'ACPR?",
    "Qui gouverne la BEI?",
    "Quel est le règlement?",
]

for q in questions:
    start = time.time()
    r = requests.post('http://localhost:8001/chat', json={
        'question': q,
        'history': []
    })
    elapsed = time.time() - start
    data = r.json()
    
    print(f"{q:40} {elapsed:5.1f}s  ({len(data.get('sources', []))} sources)")
