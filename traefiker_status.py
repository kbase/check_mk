import requests
import sys

url=sys.argv[1]
token=sys.argv[2]

cookies = dict()
cookies['kbase_session'] = token

req = requests.get(url , cookies=cookies)

counts = { 'active': 0, 'queued': 0 , 'total': 0}

for narrative in req.json()['narrative_services']:
    counts['total'] += 1
    if narrative['state'] == 'active':
        counts['active'] += 1
    if narrative['state'] == 'queued':
        counts['queued'] += 1

print (counts)
