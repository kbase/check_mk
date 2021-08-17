#!/usr/bin/python
# This is used to do a deep catalog ping as per #DEVOPS-459
# These checks excercises endpoints that require a connection to MongoDB, (rather than just the status endpoint)

import requests

import urllib3

# there is a way to only disable InsecurePlatformWarning but I can't find it now
urllib3.disable_warnings()

catalog_url = 'https://kbase.us/services/catalog'

# curl -d '{"params":["bsadkhin"],"method":"Catalog.list_favorites","version":"1.1","id":1}'  https://kbase.us/services/catalog
list_favorites_query = {
    "id": 47,
    "version": "1.1",
    "method": "Catalog.list_favorites",
    "params": ["bsadkhin"]
}
# curl -d '{"params":[{}],"method":"Catalog.list_favorite_counts","version":"1.1","id":1}'  https://kbase.us/services/catalog
list_favorite_counts = {
    "id": 47,
    "version": "1.1",
    "method": "Catalog.list_favorite_counts",
    "params": [{}]
}

catalog_ok = True
exception = None

for query in [list_favorites_query, list_favorite_counts]:
    result = requests.get(catalog_url, json=query)

    try:
        result_json = result.json()['result'][0]
        assert len(result_json) > 1
    except Exception as e:
        catalog_ok = False
        print('2 - CRITICAL - catalog deep ping failed. Likely there is a problem with mongo, and the catalog container requires a restart:', e)
        break
        
if catalog_ok:
    print('0 - OK - Catalog Deep Ping ')
    
