import requests
import os

url="https://ci.kbase.us/narrative_status/"
cookies = dict()
cookies['kbase_session'] = os.environ.get('KB_AUTH_TOKEN')

req = requests.get(url , cookies=cookies)

counts = { 'active': 0, 'queued': 0 , 'total': 0}

for narrative in req.json()['narrative_services']:
    counts['total'] += 1
    if narrative['state'] == 'active':
        counts['active'] += 1
    if narrative['state'] == 'queued':
        counts['queued'] += 1

print (counts)
