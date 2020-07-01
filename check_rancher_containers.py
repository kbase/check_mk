#!/usr/bin/python

import os
import sys
import requests
import argparse
import configparser
import json
import subprocess

parser = argparse.ArgumentParser(description='Check the status of Rancher agents and their containers.')
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

# monitor an agent
	for host in hostData:
		state=3
		stateText='UNKNOWN'

		if (host['state'] != 'active'):
			state=2
			stateText='CRITICAL'
		if (host['state'] == 'active'):
			state=0
			stateText='OK'

		instanceReq=session.get(host['links']['instances'] + '?limit=200' ,auth=(username,password))
		instanceData=instanceReq.json()['data']
	#	print len(instanceData)
	#	for instance in instanceData:
	#		print instance
		print (str(state) + ' rancher_agent_' + host['hostname'] + ' numContainers=' + str(len(instanceData)) + ';;;20;200 '  + stateText + ' host ' + host['hostname'] + ' running containers: ' + str(len(instanceData)))

# to do: monitor services inside a stack
	stackReq=session.get(urlbase+'/v2-beta/projects/' + envid + '/stacks/', auth=(username,password))
	stackData=stackReq.json()['data']

# assume there's only one
#	print (stackData)
	stackId='none'
	try:
		stackId = [i for i,j in enumerate(stackData) if j['name'] == stackname][0]
	except:
# assume no stack data; this is bad and need better handling
		sys.exit(0)

	memState = 0
	memStateTxt = 'OK'
	memCommentTxt = ''
	dockerStatsProc = subprocess.run(["docker", "stats", "--no-stream", "--no-trunc", "-a", "--format", "'{{.Container}}:{{.MemUsage}}'"], stdout=subprocess.PIPE)
#	print(dockerStatsProc)
	dockerStats = dict()
	for line in dockerStatsProc.stdout.decode('utf-8').rstrip().split('\n'):
		mylist = line.split(':')
		dockerStats[mylist[0]] = mylist[1]
	print(dockerStats)
	
	for serviceId in stackData[stackId]['serviceIds']:
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

			print (str(serviceState) + ' ' + envname + '_' + stackname + '_' + svc['name'] + ' - ' + serviceStateTxt + ' running instances: ' + str(svc['currentScale']))
	#	    print svc['healthState']

# if on a host running containers, check their resources
# assume only one instance per service
		instanceReq=session.get(urlbase+'/v2-beta/projects/' + envid + '/instances/' + svc['instanceIds'][0], auth=(username,password))
		rancherInstance=instanceReq.json()
		if rancherInstance['hostId'] == hostid:
			print (rancherInstance['name'] + ' ' + rancherInstance['externalId'])
			memUse = dockerStats[rancherInstance['externalId']]
			print (memUse)
			if memUse > 100000000:
				memState = 1
				memStateTxt = 'WARNING'
				memCommentTxt += (svc['name'] + ': ' + str(memUse) + ' ')

	print (str(memState) + ' ' + envname + '_' + stackname + '_containerMemory - ' + memStateTxt + ' big mem containers: ' + memCommentTxt)



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

