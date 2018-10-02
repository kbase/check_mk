#!/usr/bin/python

import sys
import requests
import json

import urllib3
urllib3.disable_warnings()

sw_url = sys.argv[1]
services = sys.argv[2:]

#print sw_url
#print services


for dynsvc in services:
    swdata= {
        "id": 47,
        "version": "1.1",
        "method": "ServiceWizard.get_service_status_without_restart",
         "params": [{
            "module_name": dynsvc,
            "version": None
        }]
    }

    swreq=requests.post(sw_url, json=swdata)

    try:
        dynsvcurl = swreq.json()['result'][0]['url']
    except:
        print '2 - CRITICAL - service wizard reports service ' + dynsvc + ' does not exist'
        continue

    dynsvcdata = {
        "id": 44,
        "version": "1.1",
        "method": dynsvc+".status",
         "params": []
    }
    
    dynsvcreq = requests.post(dynsvcurl,json=dynsvcdata)
    dynsvcstate=dynsvcreq.json()['result'][0]['state']
    
    svcstate=0
    svcstatetext=dynsvcstate
    if dynsvcstate == 'OK':
        svcstate=0
        svcstatetext='OK'
    else:
        svcstate=2
        svcstatetext='CRITICAL'

    print str(svcstate) + ' - ' + svcstatetext + ' - service ' + dynsvc + ' reports state ' + dynsvcstate
