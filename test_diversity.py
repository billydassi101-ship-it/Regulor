import requests
import time

start = time.time()
r = requests.post('http://localhost:8001/chat', json={
    'question': 'Quelles sont les principales règles de conformité bancaire?',
    'history': []
})
elapsed = time.time() - start

data = r.json()
print(f'✓ TIME: {elapsed:.1f}s')
print(f'Sources trouvées: {len(data.get("sources", []))}')
print('\nDiversité des sources:')
for s in data.get('sources', []):
    print(f'  - {s["filename"][:45]:45} ({int(s["similarity"]*100):2}%)')
