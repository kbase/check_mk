#!/usr/bin/python

import sys
import requests

username=sys.argv[1]
password=sys.argv[2]

session=requests.Session()
req=session.get('http://rancher.kbase.us:8080/v1/projects/1a7/hosts/', auth=(username,password))
data=req.json()['data']
for host in data:
	state=3
	stateText='UNKNOWN'

	if (host['agentState'] != 'active' or host['state'] != 'active'):
		state=2
		stateText='CRITICAL'
	if (host['agentState'] == 'active' and host['state'] == 'active'):
		state=0
		stateText='OK'

	instanceReq=session.get(host['links']['instances'],auth=(username,password))
	instanceData=instanceReq.json()['data']
	instances=''
#	print len(instanceData)
#	for instance in instanceData:
#		instances = instances + instance['name'] + ', '
#	print instances
	print str(state) + ' rancher_agent_' + host['hostname'] + ' - ' + stateText + ' host ' + host['hostname'] + ' running containers: ' + str(len(instanceData))
