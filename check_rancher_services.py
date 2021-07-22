#!/usr/bin/python

'''
This script checks the status of Rancher 1.x agents, optionally stacks and services
in given environments, and creating a dummy service in a given stack.
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

		instanceReq=session.get(host['links']['instances'] + '?limit=500' ,auth=(username,password))
		instanceData=instanceReq.json()['data']
	#	print len(instanceData)
	#	for instance in instanceData:
	#		print instance
		print (str(state) + ' rancher_agent_' + host['hostname'] + ' numContainers=' + str(len(instanceData)) + ';;;20;500 '  + stateText + ' host ' + host['hostname'] + ' running containers: ' + str(len(instanceData)))

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
### moving to separate check_rancher_containers.py till we can figure out how to
### get stats directly from rancher 1.x API
#	memState = 0
#	memStateTxt = 'OK'
#	memCommentTxt = ''
## can only check stats on the local host
## to do: try to talk to the websocket to get stats from rancher API instead
#	dockerStats = dict()

# only get stats if hostid specified (since some hosts' subprocess module is broken)
#	if hostid is not None:
#		dockerStatsProc = subprocess.run(["docker", "stats", "--no-stream", "--no-trunc", "-a", "--format", "'{{.ID}}:{{.MemUsage}}'"], stdout=subprocess.PIPE)
##		print(dockerStatsProc)
#		for line in dockerStatsProc.stdout.decode('utf-8').rstrip().split('\n'):
#			mylist = line.strip("'").split(':')
#			memUse = mylist[1].split(' ')
#			dockerStats[mylist[0]] = memUse[0]
##		print(dockerStats)

# track if there's an old dummy service that wasn't deleted
	oldDummyService = None

	for serviceId in stackData[myStack]['serviceIds']:
	#	print (serviceId)
# in that stack, look through serviceIds for named services in /v2-beta/projects/envid/services/serviceId
		serviceReq=session.get(urlbase+'/v2-beta/projects/' + envid + '/services/' + serviceId, auth=(username,password))
		svc=serviceReq.json()
		if svc['name'] == 'checkmkDummy':
			oldDummyService = svc['links']['self']
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
### this part needs lots of work
#		if hostid is not None:
#			instanceReq=session.get(urlbase+'/v2-beta/projects/' + envid + '/instances/' + svc['instanceIds'][0], auth=(username,password))
#			rancherInstance=instanceReq.json()
# to do: give a hostname, and match it up to the rancher API hostId
# otherwise, if the hostId changes, such as if a host is removed and added back to Rancher,
# the container memory check will always be OK
#			if rancherInstance['hostId'] == hostid:
##				print (rancherInstance['name'] + ' ' + rancherInstance['externalId'])
#				memUse = dockerStats[rancherInstance['externalId']]
##				print (memUse)
## crude hack: docker stats outputs human readable.  assume we only care about GB or more use
## future: better calculations
#				if 'G' in memUse:
#					memState = 1
#					memStateTxt = 'WARNING'
#					memCommentTxt += (svc['name'] + ': ' + str(memUse) + ' ;; ')

#	if hostid is not None:
#		print (str(memState) + ' ' + envname + '_' + stackname + '_containerMemory-' + hostid + ' - ' + memStateTxt + ' big mem containers on host ' + hostid + ' : ' + memCommentTxt)

	if (not conf.has_option(section,'test_create_new')):
		return None
	if (conf.getboolean(section,'test_create_new') is False):
		return None

### spin up a dummy new service
# initially copied from narrative-traefiker
	containerConfig = {u'assignServiceIpAddress': False,
                        u'createIndex': None,
                        u'created': None,
                        u'description': None,
                        u'externalId': None,
                        u'fqdn': None,
                        u'healthState': None,
                        u'kind': None,
                        u'launchConfig':   {
                            u'blkioWeight': None,
                            u'capAdd': [],
                            u'capDrop': ["MKNOD", "NET_RAW", "SYS_CHROOT", "SETUID", "SETGID", "CHOWN",
                                         "DAC_OVERRIDE", "FOWNER", "FSETID", "SETPCAP", "AUDIT_WRITE", "SETFCAP"],
                            u'cgroupParent': None,
                            u'count': None,
                            u'cpuCount': None,
                            u'cpuPercent': None,
                            u'cpuPeriod': None,
                            u'cpuQuota': None,
                            u'cpuRealtimePeriod': None,
                            u'cpuRealtimeRuntime': None,
                            u'cpuSet': None,
                            u'cpuSetMems': None,
                            u'cpuShares': None,
                            u'createIndex': None,
                            u'created': None,
                            u'dataVolumes': [],
                            u'dataVolumesFrom': [],
                            u'dataVolumesFromLaunchConfigs': [],
                            u'deploymentUnitUuid': None,
                            u'description': None,
                            u'devices': [],
                            u'diskQuota': None,
                            u'dns': [],
                            u'dnsSearch': [],
                            u'domainName': None,
                            u'drainTimeoutMs': 0,
                            u'environment': {},
                            u'externalId': None,
                            u'firstRunning': None,
                            u'healthInterval': None,
                            u'healthRetries': None,
                            u'healthState': None,
                            u'healthTimeout': None,
                            u'hostname': None,
                            u'imageUuid': u'docker:dockerhub-prod.kbase.us/containous/whoami',
                            u'instanceTriggeredStop': u'stop',
                            u'ioMaximumBandwidth': None,
                            u'ioMaximumIOps': None,
                            u'ip': None,
                            u'ip6': None,
                            u'ipcMode': None,
                            u'isolation': None,
                            u'kernelMemory': None,
                            u'kind': u'container',
                            u'labels': {u'io.rancher.scheduler.global': True,},
                            u'logConfig': {u'config': {}, u'driver': u''},
                            u'memory': None,
                            u'memoryMb': None,
                            u'memoryReservation': None,
                            u'memorySwap': None,
                            u'memorySwappiness': None,
                            u'milliCpuReservation': None,
                            u'networkLaunchConfig': None,
                            u'networkMode': u'managed',
                            u'oomScoreAdj': None,
                            u'pidMode': None,
                            u'pidsLimit': None,
                            u'ports': [],
                            u'privileged': False,
                            u'publishAllPorts': False,
                            u'readOnly': False,
                            u'removed': None,
                            u'requestedIpAddress': None,
                            u'restartPolicy': {u'name': u'never'},
                            u'runInit': False,
                            u'secrets': [],
                            u'shmSize': None,
                            u'startCount': None,
                            u'startOnCreate': True,
                            u'stdinOpen': True,
                            u'stopSignal': None,
                            u'stopTimeout': None,
                            u'tty': True,
                            u'type': u'launchConfig',
                            u'user': None,
                            u'userdata': None,
                            u'usernsMode': None,
                            u'uts': None,
                            u'uuid': None,
                            u'vcpu': 1,
                            u'volumeDriver': None,
                            u'workingDir': None},
                        u'name': 'checkmkDummy',
                        u'removed': None,
                        u'scale': 1,
                        u'secondaryLaunchConfigs': [],
                        u'selectorContainer': None,
                        u'selectorLink': None,
                        u'stackId': stackId,
                        u'startOnCreate': True,
                        u'system': False,
                        u'type': u'service',
                        u'uuid': None,
                        u'vip': None}

#       pprint(stackId)
	dummyServiceState = 3
	dummyServiceStateTxt = 'UNKNOWN'

	if (oldDummyService is not None):
		deleteOldDummySvcReq = session.delete(oldDummyService , auth=(username,password))
		if not deleteOldDummySvcReq.ok:
			dummyServiceState = 2
			dummyServiceStateTxt += ' unable to delete previously created service'
		
	newSvcReq = session.post(urlbase+'/v2-beta/projects/' + envid + '/service', json=containerConfig, auth=(username,password))
	if newSvcReq.ok:
		newDummyService = newSvcReq.json()
# need to sleep, in case an error pops up while creating the service container
# (for example, can't pull the image)
# hope 30sec should be enough time; don't want too long or check runs too long on a lot of instances
		time.sleep(30)
		newSvcState = session.get(newDummyService['links']['self'], auth=(username,password))
		dummySvc = newSvcState.json()

		if dummySvc['healthState'] == 'healthy':
			dummyServiceState = 0
			dummyServiceStateTxt = 'OK created new service successfully'
		if dummySvc['healthState'] == 'unhealthy':
			dummyServiceState = 2
			dummyServiceStateTxt = 'CRITICAL: created service but service unhealthy, state ' + str(dummySvc['healthState'])
		deleteSvcReq = session.delete(newDummyService['links']['self'] , auth=(username,password))
		if not deleteSvcReq.ok:
			dummyServiceState = 2
			dummyServiceStateTxt += ' ; unable to delete created dummy service'

	else:
		dummyServiceState = 2
		dummyServiceStateTxt = 'CRITICAL did not get 200 creating service'
	print (str(dummyServiceState) + ' ' + envname + '_' + stackname + '_createNewService - ' + dummyServiceStateTxt)


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

