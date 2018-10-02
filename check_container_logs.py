#!/usr/bin/env python

import urllib, json
import time
import sys
import re
import requests_unixsocket

# list of containers to check the logs for
# for now edit this line to hardcode which container serviceNames to check
#containers = [ "ci_searchcoordinator_1" , "ci_searchworker_1" , "ci_searchworker_2", "ci_searchworker_3", "ci_searchworker_4", "ci_searchworker_5"]
# or pass in via argv (use a shell wrapper with the args to use this way)
services = sys.argv[1:]

# defaults to retrieving 1 minute of logs
now = time.time() - (20*60)

status = dict()

session=requests_unixsocket.Session()
#r=session.get('http+unix://%2fvar%2frun%2fdocker.sock/containers/ci_searchworker_11/logs?stderr=1&stdout=1&tail=1&since=' + str(int(now)))

containersReq=session.get('http+unix://%2fvar%2frun%2fdocker.sock/containers/json' )
containers=containersReq.json()
#print containers

for serviceName in services:
  status = 3
  statusText = 'UNKNOWN'

#u'Labels': {u'io.rancher.container.name': u'ci-core-searchcoordinator-1'
#u'io.rancher.project_service.name':
#  print [ (i,j) for i,j in enumerate(containers) if ( 'io.rancher.container.name' in j['Labels'] and re.search(serviceName,j['Labels']['io.rancher.container.name'] ) ]
#  serviceContainers = [ i for i,j in enumerate(containers) if ( 'io.rancher.project_service.name' in j['Labels'] and j['Labels']['io.rancher.project_service.name'] == serviceName ) ]
  serviceContainers = [ i for i,j in enumerate(containers) if ( 'io.rancher.container.name' in j['Labels'] and j['Labels']['io.rancher.container.name'] == serviceName ) ]

  if (len(serviceContainers) < 1):
      status = 2
      statusText = 'CRITICAL: container not running'
      print str(status) + ' containerlogs_' + serviceName + ' - ' + statusText
      continue
    
# for now just pick first container off of list
  container = containers[serviceContainers[0]]
#  print container
#  print container['State']
  containerName=container['Names'][0]

# to do: try to filter coordinator diag lines

  r=session.get('http+unix://%2fvar%2frun%2fdocker.sock/containers' + containerName + '/logs?stderr=1&stdout=1&tail=1&since=' + str(int(now)) )

  if r.status_code == 200:

    if (len(r.content) > 10):
      status = 0
      statusText = 'OK: last line: '
    else:
      status = 1
      statusText = 'WARNING: no recent logs found'
# temporary while waiting for heartbeat
      status = 0
      statusText = 'OK: no recent logs found'
  else:
      status = 3
      statusText = 'UNKNOWN: no container found'

#  print container.keys()
#  if ('State' not in container.keys() or container['State']['Status'] != 'running'):
  if ('State' not in container.keys() or container['State'] != 'running'):
      status = 2
      statusText = 'CRITICAL: container not running'


  print str(status) + ' containerlogs_' + serviceName + ' - ' + statusText + ' ' + r.content.strip()
