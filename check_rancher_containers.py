#!/usr/bin/python

'''
This script checks the memory use of Docker containers on a Rancher 1.x agent.
'''

import os
import sys
import requests
import argparse
import configparser
import json
import subprocess
import time
from pprint import pprint

parser = argparse.ArgumentParser(description='Check the resource use (memory) of containers managed by Rancher 1.x.')
parser.add_argument('--config-file', dest='configfile', required=True,
		    help='Path to config file (INI format). (required)')
parser.add_argument('--config-sections', dest='sections', nargs='*',
		    help='Section(s) in config file to use. (default to all sections in config file)')
args = parser.parse_args()

configfile=args.configfile
conf=configparser.ConfigParser()
conf.read(configfile)
#print (conf.sections())

# skip to end for loop that processes each section

def process_section(conf, section):

# include the port if needed
	urlbase=conf[section]['rancher_url']
# would be better to use envname and query the api to find envid
# but the envid should seldom if ever change so getting on cmdline ok
	envid=conf[section]['rancher_envid']
	envname=conf[section]['rancher_envname']
	stackname=conf[section]['rancher_stackname']
	username=conf[section]['rancher_accesskey']
	password=conf[section]['rancher_secretkey']
# also would be better to do a hostname lookup with os.uname()[1] and
# compare to hostname in rancher data
# but for now this is also ok
	hostid=None
	if conf.has_option(section,'rancher_hostid'):
		hostid=conf[section]['rancher_hostid']

# look for these services (a JSON-formatted list, requires double-quotes around strings)
	try:
		monitoredServices = json.loads(conf.get(section,'service_list'))
	except:
		monitoredServices = []
	#print (monitoredServices)

	session=requests.Session()
	hostsReq=session.get(urlbase+'/v2-beta/projects/' + envid + '/hosts/', auth=(username,password))
	hostData=hostsReq.json()['data']


# to do: monitor services inside a stack
	stackReq=session.get(urlbase+'/v2-beta/projects/' + envid + '/stacks/', auth=(username,password))
	stackData=stackReq.json()['data']

# assume there's only one
#	print (stackData)
	myStack='none'
	try:
		myStack = [i for i,j in enumerate(stackData) if j['name'] == stackname][0]
	except:
# assume no stack data; this is bad and need better handling
		sys.exit(0)
	stackId = stackData[myStack]['id']

### this part needs a lot of work
	memState = 0
	memStateTxt = 'OK'
	memCommentTxt = ''
## can only check stats on the local host
## to do: try to talk to the websocket to get stats from rancher API instead
	dockerStats = dict()

# only get stats if hostid specified (since some hosts' subprocess module is broken)
	if hostid is not None:
		dockerStatsProc = subprocess.run(["docker", "stats", "--no-stream", "--no-trunc", "-a", "--format", "'{{.ID}}:{{.MemUsage}}'"], stdout=subprocess.PIPE)
#		print(dockerStatsProc)
		for line in dockerStatsProc.stdout.decode('utf-8').rstrip().split('\n'):
			mylist = line.strip("'").split(':')
			memUse = mylist[1].split(' ')
			dockerStats[mylist[0]] = memUse[0]
#		print(dockerStats)

	for serviceId in stackData[myStack]['serviceIds']:
	#	print (serviceId)
# in that stack, look through serviceIds for named services in /v2-beta/projects/envid/services/serviceId
		serviceReq=session.get(urlbase+'/v2-beta/projects/' + envid + '/services/' + serviceId, auth=(username,password))
		svc=serviceReq.json()
		if svc['name'] in monitoredServices:
			serviceState = 3
			serviceStateTxt = 'UNKNOWN'

			if svc['healthState'] == 'healthy':
				serviceState = 0
				serviceStateTxt = 'OK'
			if svc['healthState'] == 'unhealthy':
				serviceState = 2
				serviceStateTxt = 'CRITICAL'

	#		print (str(serviceState) + ' ' + envname + '_' + stackname + '_' + svc['name'] + ' - ' + serviceStateTxt + ' running instances: ' + str(svc['currentScale']))
	#	    print svc['healthState']

# if on a host running containers, check their resources
# assume only one instance per service
### this part needs lots of work
		if hostid is not None:
			instanceReq=session.get(urlbase+'/v2-beta/projects/' + envid + '/instances/' + svc['instanceIds'][0], auth=(username,password))
			rancherInstance=instanceReq.json()
# to do: give a hostname, and match it up to the rancher API hostId
# otherwise, if the hostId changes, such as if a host is removed and added back to Rancher,
# the container memory check will always be OK
			if rancherInstance['hostId'] == hostid:
#				print (rancherInstance['name'] + ' ' + rancherInstance['externalId'])
				memUse = dockerStats[rancherInstance['externalId']]
#				print (memUse)
## crude hack: docker stats outputs human readable.  assume we only care about GB or more use
## future: better calculations
				if 'G' in memUse:
					memState = 1
					memStateTxt = 'WARNING'
					memCommentTxt += (svc['name'] + ': ' + str(memUse) + ' ;; ')

	if hostid is not None:
		print (str(memState) + ' ' + envname + '_' + stackname + '_containerMemory-' + hostid + ' - ' + memStateTxt + ' big mem containers on host ' + hostid + ' : ' + memCommentTxt)

### spin up a dummy new service
### see check_rancher_services.py

# in each service find the last logs?  may be hard, need websocket

# main loop
# if args provided, use them, otherwise use sections from config file
if args.sections:
	sections = args.sections
else:
	sections = conf.sections()

for section in sections:
#	print (section)
	process_section(conf, section)

