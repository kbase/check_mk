#!/usr/bin/python

import sys
import requests

# include the port if needed
urlbase=sys.argv[1]
envid=sys.argv[2]
username=sys.argv[3]
password=sys.argv[4]

session=requests.Session()
req=session.get(urlbase+'/v1/projects/' + envid + '/hosts/', auth=(username,password))
data=req.json()['data']
for host in data:
	state=3
	stateText='UNKNOWN'

	if (host['state'] != 'active'):
		state=2
		stateText='CRITICAL'
	if (host['state'] == 'active'):
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
