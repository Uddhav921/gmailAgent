import urllib.request
import json

req = urllib.request.Request(
    'http://localhost:8000/admin/send-test', 
    data=b'{"to":"uddhavtaur6@gmail.com","subject":"Test 2","body":"Hello"}', 
    headers={'Content-Type': 'application/json'}, 
    method='POST'
)

try:
    urllib.request.urlopen(req)
except Exception as e:
    print(e.read().decode())
