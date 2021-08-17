#!/usr/bin/python
# This is used to do a deep catalog ping as per #DEVOPS-459
# This excercises endpoints that require a connection to mongo, rather than just the status endpoint

import sys
import requests
import json

import urllib3
# there is a way to only disable InsecurePlatformWarning but I can't find it now
urllib3.disable_warnings()

catalog_url = https://kbase.us/services/catalog
services = sys.argv[2:]



# curl -d '{"params":["bsadkhin"],"method":"Catalog.list_favorites","version":"1.1","id":1}'  https://kbase.us/services/catalog
list_favorites_query =  {
        "id": 47,
        "version": "1.1",
        "method": "Catalog.list_favorites",
        "params": [{"params":["bsadkhin"]}]
    }

# curl -d '{"params":[{}],"method":"Catalog.list_favorite_counts","version":"1.1","id":1}'  https://kbase.us/services/catalog
list_favorite_counts =  {
        "id": 47,
        "version": "1.1",
        "method": "Catalog.list_favorite_counts",
        "params": [{"params":[{}]}]
    }

for query in [list_favorites_query, list_favorite_counts]:
    query=requests.get(sw_url, json=swdata)

    try:
        dynsvcurl = swreq.json()['result'][0]['url']
        print '0 - OK - service ' + dynsvc + ' not responding correctly'
    except:
        print '2 - CRITICAL - catalog deep ping failed '
        continue

