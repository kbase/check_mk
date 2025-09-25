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
import sqlite3
# this requires python 3.4
import pathlib
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

# monitor rancher agents
	for host in hostData:
		state=3
		stateText='UNKNOWN'

		if (host['state'] != 'active'):
			state=2
			stateText='CRITICAL'
		if (host['state'] == 'active'):
			state=0
			stateText='OK'
		if (host['state'] == 'inactive'):
			state=1
			stateText='WARNING'

		instanceReq=session.get(host['links']['instances'] + '?limit=500' ,auth=(username,password))
		instanceData=instanceReq.json()['data']
	#	print len(instanceData)
	#	for instance in instanceData:
	#		print instance
		print (str(state) + ' rancher_agent_' + host['hostname'] + ' numContainers=' + str(len(instanceData)) + ';;;20;500 '  + stateText + ' host ' + host['hostname'] + ' ; state: ' + host['state'] + ' ; running containers: ' + str(len(instanceData)))

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

##### test health of listed services (if any)
# track if there's an old dummy service that wasn't deleted
	oldDummyService = None

	for serviceId in stackData[myStack]['serviceIds']:
	#	print (serviceId)
# in the stack, look through serviceIds for named services in /v2-beta/projects/envid/services/serviceId
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


##### test overall stack health
	if (conf.has_option(section,'test_stack_health') and conf.getboolean(section,'test_stack_health') is True):
		stackState = 3
		stackStateTxt = 'UNKNOWN'
		stackExtraTxt = ''

		if (conf.has_option(section,'stack_health_dir')):
			stackHealthFile = conf[section]['stack_health_dir'] + '/' + envname + '_' + stackname + '_stackHealth.db'
			stackPath = pathlib.Path(stackHealthFile)
			# make sure the db file exists, in case stack has never been checked
			# (should also error immediately if a bad path is provided in the config file)
			if (not stackPath.exists()):
				conn = sqlite3.connect(stackHealthFile)
				conn.execute('CREATE TABLE badServices (serviceId TEXT PRIMARY KEY, serviceName TEXT, lastUpdate DATETIME DEFAULT CURRENT_TIMESTAMP)')
				conn.commit()
				conn.close()

		conn = sqlite3.connect(stackHealthFile)

		if stackData[myStack]['healthState'] == 'healthy':
			stackState = 0
			stackStateTxt = 'OK'
			if (conf.has_option(section,'stack_health_dir')):
# just assume all services are healthy if stack is, and delete all bad services from the db
				conn.execute('DELETE FROM badServices')
				conn.commit()

##### if stack reports degraded, look through services in stack to verify
# (rancher 1 doesn't really report this very well)
		else:
			# we're trolling this again, meh. but only when stack is unhealthy, so don't worry about it
			for serviceId in stackData[myStack]['serviceIds']:
				healthServiceReq=session.get(urlbase+'/v2-beta/projects/' + envid + '/services/' + serviceId, auth=(username,password))
				healthSvc=healthServiceReq.json()
#				print (healthSvc['id'] + ' ' + healthSvc['healthState'])
				if (healthSvc['healthState'] == 'healthy' or healthSvc['healthState'] == 'started-once'):
					conn.execute('DELETE FROM badServices WHERE serviceId = ?', [ healthSvc['id'] ] )
					conn.commit()
				else:
					conn.execute('INSERT OR IGNORE INTO badServices (serviceId, serviceName) VALUES (?,?)', [ healthSvc['id'], healthSvc['name']] )
					conn.commit()
					

			cursor = conn.cursor()
			# this should return only services that have been unhealthy for a while (in theory persistently unhealthy)
			query = "SELECT serviceName FROM badServices WHERE (datetime(lastUpdate) < datetime('now','-" + conf[section]['stack_health_age'] + " seconds' ))"
#			print (query)
			cursor.execute(query)

			# fetchall isn't great in theory, but in practice we should have very few rows in these tables
			badServices = cursor.fetchall()
			if (len(badServices) == 0):
				# all services now OK, so assume stack OK
				stackState = 0
				stackStateTxt = 'OK'
			else:
				stackState = 1
				stackStateTxt = 'WARNING'
				stackExtraTxt = ' ; bad services: ' + ' '.join([ t[0] for t in badServices])
				query = "SELECT serviceName FROM badServices WHERE (datetime(lastUpdate) < datetime('now','-" + str(2 * int(conf[section]['stack_health_age'])) + " seconds' ))"
#			print (query)
				cursor.execute(query)
				reallyBadServices = cursor.fetchall()
				if (len(reallyBadServices) > 0):
					stackState = 2
					stackStateTxt = 'CRITICAL'

		conn.close()
		print (str(stackState) + ' ' + envname + '_' + stackname + '_stackHealth - ' + stackStateTxt + ' stack health is ' + stackData[myStack]['healthState'] + stackExtraTxt)

	if (not conf.has_option(section,'test_create_new')):
		return None
	if (conf.getboolean(section,'test_create_new') is False):
		return None

##### if requested in config, test spinning up a dummy new service
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
		for i in range(5):
			time.sleep(5)
			newSvcState = session.get(newDummyService['links']['self'], auth=(username,password))
			dummySvc = newSvcState.json()

			# this doesn't detect if the service has been deleted
			# (but does detect if existing service is not healthy)
			if dummySvc['healthState'] == 'healthy':
				dummyServiceState = 0
				dummyServiceStateTxt = 'OK created new service successfully'
				break
			if dummySvc['healthState'] != 'healthy':
				dummyServiceState = 1
				dummyServiceStateTxt = 'WARNING: created service but service not healthy, state ' + str(dummySvc['healthState'])

		deleteSvcReq = session.delete(newDummyService['links']['self'] , auth=(username,password))
		if not deleteSvcReq.ok:
			dummyServiceState = 1
			dummyServiceStateTxt += ' ; unable to delete created dummy service'

	else:
		dummyServiceState = 1
		dummyServiceStateTxt = 'WARNING: did not get 200 creating service: ' + str(newSvcReq.text)
	print (str(dummyServiceState) + ' ' + envname + '_' + stackname + '_createNewService - ' + dummyServiceStateTxt)


##### main loop
# if args provided, use them, otherwise use sections from config file
if args.sections:
	sections = args.sections
else:
	sections = conf.sections()

for section in sections:
#	print (section)
	process_section(conf, section)
