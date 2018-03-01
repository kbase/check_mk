#!/usr/bin/env python

import urllib, json
import time
import sys
import requests_unixsocket

# list of containers to check the logs for
# for now edit this line to hardcode which container names to check
#containers = [ "ci_searchcoordinator_1" , "ci_searchworker_1" , "ci_searchworker_2", "ci_searchworker_3", "ci_searchworker_4", "ci_searchworker_5"]
# or pass in via argv
# (for check_mk use a shell wrapper)
containers = sys.argv[1:]

# defaults to retrieving 20 minute of logs
now = time.time() - (20*60)

status = dict()

session=requests_unixsocket.Session()
#r=session.get('http+unix://%2fvar%2frun%2fdocker.sock/containers/ci_searchworker_11/logs?stderr=1&stdout=1&tail=1&since=' + str(int(now)))

for name in containers:
  status = 3
  statusText = 'UNKNOWN'

# to do: try to filter coordinator diag lines
# may need tail=larger to get enough lines
  statusReq=session.get('http+unix://%2fvar%2frun%2fdocker.sock/containers/' + name + '/json' )
  state=statusReq.json()

  r=session.get('http+unix://%2fvar%2frun%2fdocker.sock/containers/' + name + '/logs?stderr=1&stdout=1&tail=1&since=' + str(int(now)) )

  if r.status_code == 200:

    if (len(r.content) > 10):
      status = 0
      statusText = 'OK: last line: '
    else:
      status = 1
      statusText = 'WARNING: no recent logs found'
  else:
      status = 3
      statusText = 'UNKNOWN: no container found'

  if ('State' not in state.keys() or state['State']['Status'] != 'running'):
      status = 2
      statusText = 'CRITICAL: container not running'


  print str(status) + ' containerlogs_' + name + ' - ' + statusText + ' ' + r.content.strip()
