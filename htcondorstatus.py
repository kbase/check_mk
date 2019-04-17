#!/usr/bin/python

#
# Be sure to populate the *host's* /etc/condor/ directory appropriately!
# It needs condor_config, condor_config.local, and password from the
# manager container's /etc/condor/ directory.
#

import sys
import configparser
import re
import htcondor
import classad
import requests

import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecurePlatformWarning)
urllib3.disable_warnings(urllib3.exceptions.SNIMissingWarning)
#requests.packages.urllib3.disable_warnings()

# magic numbers:
# https://htcondor-wiki.cs.wisc.edu/index.cgi/wiki?p=MagicNumbers

configfile=sys.argv[1]
conf=configparser.ConfigParser()
conf.read(configfile)
#print conf.sections()
authUrl='https://kbase.us/services/auth/me'

#collector = htcondor.Collector('host:9618')
collector = htcondor.Collector()

collectors = collector.query(htcondor.AdTypes.Collector, "true", ["Name"])
numCollectors = len(collectors)
negotiators = collector.query(htcondor.AdTypes.Negotiator, "true", ["Name"])
numNegotiators = len(negotiators)

collectorState=3
collectorStateText='UNKNOWN'
negotiatorState=3
negotiatorStateText='UNKNOWN'

if (numCollectors < 1):
	collectorState=2
	collectorStateText='CRITICAL'
if (numCollectors > 0):
	collectorState=0
	collectorStateText='OK'
print str(collectorState) + ' Condor_num_collectors collectors=' + str(numCollectors) + ' ' + collectorStateText + ' - ' + str(numCollectors) + ' collectors running'

if (numNegotiators < 1):
	negotiatorState=2
	negotiatorStateText='CRITICAL'
if (numNegotiators > 0):
	negotiatorState=0
	negotiatorStateText='OK'
print str(negotiatorState) + ' Condor_num_negotiators negotiators=' + str(numNegotiators) + ' ' + negotiatorStateText + ' - ' + str(numNegotiators) + ' negotiators running'

slots = collector.query(htcondor.AdTypes.Startd, "true")

# generate these on the fly in the slot or job loop
jobCounts = {
	'njs': 0,
	'bigmemlong': 0,
	'bigmem': 0,
	'kb_upload': 0
}
slotCounts = {}

# in this loop:
# clients (done)
for slot in slots:
#	print slot
	slotState=3
	slotStateText='UNKNOWN'
	# these are just guesses
	if slot['Activity'] in ['Busy','Idle','Benchmarking']:
		slotState=0
		slotStateText='OK'
	if slot['Activity'] in ['None','Retiring','Vacating','Suspended']:
		slotState=1
		slotStateText='WARNING'
	if slot['Activity'] in ['Killing']:
		slotState=2
		slotStateText='CRITICAL'
	# don't report dynamic slots
	if 'DynamicSlot' in slot.keys():
		continue

	print str(slotState) + ' Condor_slot_' + slot['Name'] + ' state=' + str(slot['Activity']) + ' ' + slotStateText + ' - slot ' + slot['Name'] + ' in clientgroup ' + slot['CLIENTGROUP'] + ' is in state ' + slot['Activity']
	# need to check for this key, and create if not exists
	if slot['CLIENTGROUP'] not in slotCounts:
		slotCounts[slot['CLIENTGROUP']] = {}
		slotCounts[slot['CLIENTGROUP']]['Total'] = 0
		slotCounts[slot['CLIENTGROUP']]['Idle'] = 0
	slotCounts[slot['CLIENTGROUP']]['Total'] += 1
	if slot['Activity'] not in slotCounts[slot['CLIENTGROUP']]:
		slotCounts[slot['CLIENTGROUP']][slot['Activity']] = 0
	slotCounts[slot['CLIENTGROUP']][slot['Activity']] += 1
	
# this doesn't pick up clientgroups in condor but not in config file
for clientgroup in conf.sections():
	if clientgroup in ['DEFAULT','global']:
		continue
	try:
		clientgroupState=3
		clientgroupStateText='UNKNOWN'

		if slotCounts[clientgroup]['Total'] >= conf.getint(clientgroup,'minTotal.warn'):
			clientgroupState=0
			clientgroupStateText='OK'
		if slotCounts[clientgroup]['Idle'] >= conf.getint(clientgroup,'minIdle.warn'):
			clientgroupState=0
			clientgroupStateText='OK'
		if slotCounts[clientgroup]['Total'] < conf.getint(clientgroup,'minTotal.warn'):
			clientgroupState=1
			clientgroupStateText='WARNING'
		if slotCounts[clientgroup]['Idle'] < conf.getint(clientgroup,'minIdle.warn'):
			clientgroupState=1
			clientgroupStateText='WARNING'
		if slotCounts[clientgroup]['Total'] < conf.getint(clientgroup,'minTotal.crit'):
			clientgroupState=2
			clientgroupStateText='CRITICAL'
		if slotCounts[clientgroup]['Idle'] < conf.getint(clientgroup,'minIdle.crit'):
			clientgroupState=2
			clientgroupStateText='CRITICAL'

#		print str(clientgroupState) + ' Condor_clientgroup_' + clientgroup + ' - ' + clientgroupStateText + ' - clientgroup ' + clientgroup + ' has ' + str(slotCounts[clientgroup]['Total']) + ' total workers and ' + str(slotCounts[clientgroup]['Idle']) + ' idle workers'
		print "%d Condor_clientgroup_%s %s=%d;%d;%d;0 %s - clientgroup %s has %d total workers and %d idle workers" % (clientgroupState,clientgroup,clientgroup,slotCounts[clientgroup]['Idle'],conf.getint(clientgroup,'minIdle.warn'),conf.getint(clientgroup,'minIdle.crit'),clientgroupStateText,clientgroup,slotCounts[clientgroup]['Total'],slotCounts[clientgroup]['Idle'])

	except:
		print str(3) + ' Condor_clientgroup_' + clientgroup + ' - UNKNOWN - clientgroup ' + clientgroup + ' has no workers in any state'

schedddaemon = collector.locateAll(htcondor.DaemonTypes.Schedd)[0]

clientgroupre=re.compile('.*CLIENTGROUP == .(\w+)')
tokenre=re.compile('.*KB_AUTH_TOKEN=(\w+)')

schedd = htcondor.Schedd(schedddaemon)
# maybe limit to jobs which have not completed?
jobs = schedd.xquery()

# need to make these clientgroup-specific?
runningJobCount=0
idleJobCount=0
maxRunningTime=0
maxIdleTime=0
longRunningJobList=[]
longIdleJobList=[]

# the default state should probably be OK for these
idleTimeState=0
idleTimeStateText='OK'
runningTimeState=0
runningTimeStateText='OK'
idleCountState=0
idleCountStateText='OK'
runningCountState=0
runningCountStateText='OK'

expiredTokenState=0
expiredTokenStateText='OK'
expiredTokenJobsList=[]

# in this loop:
# jobs queued/queued time (is this idle?) (still to do)
# jobs in progress/in progress time (still to do)
# jobs held (still to do)
for job in jobs:

    jobname='[undefined]'
    acctgroup='[undefined]'
    clientgroup='[undefined]'
    token='[undefined]'
    try:
	jobname=job['JobBatchName']
    except:
	jobname=job['GlobalJobId']
    try:
	acctgroup=job['AcctGroup']
    except:
	acctgroup='undefined'
    try:
	match=clientgroupre.match(str(job['Requirements']))
	clientgroup=match.group(1)
    except Exception as e:
#	print e
	clientgroup='unknown'
    try:
	tokenmatch=tokenre.match(str(job['Environment']))
	token=tokenmatch.group(1)
    except:
	token='unknown'

# these loops could be made better by storing the data in a structure instead of
# variables with "running" or "idle" in the name
# also could just save maxXtime and compare at the end

# 2 is running; alert on long run times
    if job['JobStatus'] == 2:
#	print job
#	print jobname + ' : ' + acctgroup + ' ' + str(job['JobStatus']) + ' ' + str(job['JobStartDate']) + ' ' + str(job['ServerTime'])
#	print job['Environment']
#	print token

# to do: 
# bail if token==unknown
# curl -s -H "Authorization: token" https://kbase.us/services/auth/me
# if Unauthorized, then alert; print job id, slot, acctgroup
	headers = {'authorization': token}
	r = requests.get(authUrl, headers=headers)
# in this block, add jobs to a list?  then alert later if list length > 0?
	if r.status_code != 200:
		expiredTokenJobsList.append(str(job['ClusterId']) + ' (running) ' + job['RemoteHost'] + ' ' + jobname + ' ' +acctgroup)

	jobRunningTime = (job['ServerTime'] - job['JobCurrentStartDate'])/60
	if jobRunningTime > maxRunningTime:
		maxRunningTime=jobRunningTime
	if jobRunningTime > conf.getint('global','runtime.warn'):
                if runningTimeState != 2:
                       runningTimeState=1
                       runningTimeStateText='WARNING'
                longRunningJobList.append( "%d (%s, %s, %s, %d min)"%(job['ClusterId'],acctgroup,jobname,job['RemoteHost'],jobRunningTime))
	if jobRunningTime > conf.getint('global','runtime.crit'):
		runningTimeState=2
		runningTimeStateText='CRITICAL'
	runningJobCount += 1
# 1 is idle; alert on long queue times
    if job['JobStatus'] == 1:

	idleJobCount += 1

	jobIdleTime = (job['ServerTime'] - job['QDate'])/60
	if jobIdleTime > maxIdleTime:
		maxIdleTime=jobIdleTime
	if jobIdleTime > conf.getint('global','idletime.warn'):
               if idleTimeState != 2:
                       idleTimeState=1
                       idleTimeStateText='WARNING'
	longIdleJobList.append( "%d (%s, %s, %s, %dmin)"%(job['ClusterId'],acctgroup,clientgroup,jobname,jobIdleTime))
	if jobIdleTime > conf.getint('global','idletime.crit'):
		idleTimeState=2
		idleTimeStateText='CRITICAL'

# report idle jobs with expired tokens
# moving to here to make it easier to bypass if needed
	headers = {'authorization': token}
	r = requests.get(authUrl, headers=headers)
	if r.status_code != 200:
		expiredTokenJobsList.append(str(job['ClusterId']) + ' (idle) ' + acctgroup)


# these do not properly capture the longest jobs
# probably should sort the list by time then take longest
longRunningJobsText = ', '.join(longRunningJobList[0:10])
longIdleJobsText = ', '.join(longIdleJobList[0:10])
expiredTokenJobsText = ', '.join(expiredTokenJobsList)

if runningJobCount > conf.getint('global','runcount.warn'):
	runningCountState=1
	runningCountStateText='WARNING'
if runningJobCount > conf.getint('global','runcount.crit'):
	runningCountState=2
	runningCountStateText='CRITICAL'
if idleJobCount > conf.getint('global','idlecount.warn'):
	idleCountState=1
	idleCountStateText='WARNING'
if idleJobCount > conf.getint('global','idlecount.crit'):
	idleCountState=2
	idleCountStateText='CRITICAL'

if len(expiredTokenJobsList) > 0:
	expiredTokenState=1
	expiredTokenStateText='WARNING'
	
print "%d Condor_idleCount idleCount=%d;%d;%d;0 %s - idleCount %d jobs idle" % (idleCountState,idleJobCount,conf.getint('global','idlecount.warn'),conf.getint('global','idlecount.crit'),idleCountStateText,idleJobCount)
print "%d Condor_runningCount runningCount=%d;%d;%d;0 %s - runningCount %d jobs running" % (runningCountState,runningJobCount,conf.getint('global','runcount.warn'),conf.getint('global','runcount.crit'),runningCountStateText,runningJobCount)

print "%d Condor_idleTime idleTime=%d;%d;%d;0 %s - idleTime max %d minutes, sample 10 jobIds (minutes): %s" % (idleTimeState,maxIdleTime,conf.getint('global','idletime.warn'),conf.getint('global','idletime.crit'),idleTimeStateText,maxIdleTime,longIdleJobsText)
print "%d Condor_runningTime runningTime=%d;%d;%d;0 %s - runningTime max %d minutes, sample 10 jobIds (minutes): %s" % (runningTimeState,maxRunningTime,conf.getint('global','runtime.warn'),conf.getint('global','runtime.crit'),runningTimeStateText,maxRunningTime,longRunningJobsText)

print "%d Condor_expiredTokens - %s - %d jobs with expired tokens: %s" % (expiredTokenState,expiredTokenStateText,len(expiredTokenJobsList),expiredTokenJobsText)



#    print jobname
#    print job['JobStartDate']
#    print job['QDate']
#    print job['ServerTime']
	
#print str(runningJobCount) + ' running jobs'
#print slotCounts
