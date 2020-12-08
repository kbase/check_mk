#!/usr/bin/env python3

import subprocess
import json
from pprint import pprint

status_strings = ['OK','WARNING','CRITICAL','UNKNOWN']

#/opt/mc/mc admin info --json  minio
#out=subprocess.run(['/opt/mc/mc','admin','info','--json','minio'])
# need --insecure with recent mc clients and self-signed certs
out=subprocess.check_output(['/opt/mc/mc','admin','info','--insecure','--json','minio'])

# default to OK
status = 0

#print(out)

minioInfo = json.loads(out)
#pprint(minioInfo)

# global mode
# alert if not "online"
clusterModeString = 'cluster: ' + minioInfo['info']['mode'] 
if (minioInfo['info']['mode'] != 'online'):
    # not sure what other states are possible, some might be warning only
    status = 2

serverStateString = ''
driveStateString = ''

for server in (minioInfo['info']['servers']):
    # server state; alert if not "ok"
    serverStateString += ' ' + server['endpoint'] + ' : ' + server['state']
    if (server['state'] != 'ok'):
        # not sure what other states are possible, some might be warning only
        status = 2
    for drive in (server['drives']):
# if there's an unformatted drive on a remote, it has only these keys
# if there's a healthy drive on a remote, or an unformatted drive on the
# serving instance, there is a path key as well
# so...construct an endpoint from server['endpoint']+drive['path']
# and if drive['path'] doesn't exist, use drive['endpoint'] 
        try:
            driveEndpoint = server['endpoint'] + ':' + drive['path']
        except:
# try to strip leading "https:" from this to be consistent with above
            driveEndpoint = drive['endpoint'].replace('https://','')
# drive state; alert if not "ok"
        if (drive['state'] != 'ok' or 'healing' in drive):
            # assume a missing drive is not critical
            status = 1
            driveExtraInfo = ''
            if ('healing' in drive):
                driveExtraInfo = '(healing)'
            # since there are so many drives, only add unhealthy ones to output
            driveStateString += ' ' + driveEndpoint + ' : ' + drive['state'] + ' driveExtraInfo

print ("%d Minio_status - %s - %s %s %s" % (status, status_strings[status], clusterModeString, serverStateString, driveStateString) )
