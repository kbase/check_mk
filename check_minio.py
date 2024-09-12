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
    if (server['state'] != 'online'):
        # not sure what other states are possible, some might be warning only
        status = 2
    for drive in (server['drives']):
        driveEndpoint = drive['endpoint'].replace('https://','')
# drive state; alert if not "ok"
        if (drive['state'] != 'ok' or 'healing' in drive):
            # assume a missing drive is not critical
            status = 1
            driveExtraInfo = ''
            if ('healing' in drive):
                driveExtraInfo = '(healing)'
            # since there are so many drives, only add unhealthy ones to output
            driveStateString += ' ' + driveEndpoint + ' : ' + drive['state'] + ' ' + driveExtraInfo

print ("%d MinIO_status - %s - %s %s %s" % (status, status_strings[status], clusterModeString, serverStateString, driveStateString) )

exit (status)
