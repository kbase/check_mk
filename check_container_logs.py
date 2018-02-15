#!/usr/bin/env python

import urllib, json
#from os import walk, listdir
#from os.path import isdir,join
import time
import requests_unixsocket

# list of containers to check the logs for
# for now edit this line to hardcode which container names to check
containers = [ "ci_coordinator_1" , "ci_worker_1", "ci_worker_2" ]

# defaults to retrieving 1 minute of logs
now = time.time() - (1*60)

status = dict()

session=requests_unixsocket.Session()
#r=session.get('http+unix://%2fvar%2frun%2fdocker.sock/containers/ci_worker_11/logs?stderr=1&stdout=1&tail=1&since=' + str(int(now)))

for name in containers:
  status = 3
  statusText = 'UNKNOWN'
  checkOutput = ''

# to do: try to filter coordinator diag lines
# may need tail=larger to get enough lines
  r=session.get('http+unix://%2fvar%2frun%2fdocker.sock/containers/' + name + '/logs?stderr=1&stdout=1&tail=1&since=' + str(int(now)) )

  if r.status_code == 200:

    if (len(r.content) > 10):
      status = 0
      statusText = 'OK: last line: '
    else:
      status = 2
      statusText = 'CRITICAL: no logs found'
  else:
      status = 3
      statusText = 'UNKNOWN: no container found'

  print str(status) + ' containerlogs_' + name + ' - ' + statusText + ' ' + r.content.strip()
