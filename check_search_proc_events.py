#!/usr/bin/env python

import urllib, json
import time
import datetime
import pytz
import sys
from pymongo import MongoClient

hostname=sys.argv[1]
username=sys.argv[2]
password=sys.argv[3]

warnInterval=3600 * 2
critInterval=3600 * 3
warnAgo=datetime.datetime.fromtimestamp(time.time() - warnInterval, pytz.timezone("US/Pacific"))
critAgo=datetime.datetime.fromtimestamp(time.time() - critInterval, pytz.timezone("US/Pacific"))

countsStatus = {
	'READY': {
		'warn': 100,
		'crit': 200
	},
	'UNPROC': {
		'warn': 100,
		'crit': 200
	},
}

client=MongoClient(hostname)
db=client.search
db.authenticate(username,password)
events=db.searchEvents

status = 3
statusText = 'UNKNOWN'
extraText = 'unknown state'

warnCount = events.count_documents({"status":"PROC","updte": {"$lt": warnAgo}})
critCount = events.count_documents({"status":"PROC","updte": {"$lt": critAgo}})
if (warnCount == 0):
  status = 0
  statusText = 'OK'
  extraText = 'no PROC events found older than ' + str(warnInterval) + ' seconds'
if (warnCount > 0):
  status = 1
  statusText = 'WARNING'
  extraText = str(warnCount) + ' PROC events found older than ' + str(warnInterval) + ' seconds'
if (critCount > 0):
  status = 2
  statusText = 'CRITICAL'
  extraText = str(critCount) + ' PROC events found older than ' + str(critInterval) + ' seconds'

print (str(status) + ' searcheventage' + ' - ' + statusText + ' ' + extraText)

eventCount={}
eventCount['UNPROC'] = events.count_documents({"status":"UNPROC"})
eventCount['READY'] = events.count_documents({"status":"READY"})
totalEventCount= eventCount['READY'] + eventCount['UNPROC']

for eventstate in ('READY','UNPROC'):
	countStatus=3
	countStatusText='UNKNOWN'
	extraText = str(eventCount[eventstate]) + ' events in state ' + eventstate
	if (eventCount[eventstate] <= countsStatus[eventstate]['warn']):
		countStatus=0
		countStatusText='OK'
	if (eventCount[eventstate] > countsStatus[eventstate]['warn']):
		countStatus=1
		countStatusText='WARNING'
	if (eventCount[eventstate] > countsStatus[eventstate]['crit']):
		countStatus=2
		countStatusText='CRITICAL'
	print (str(countStatus) + ' searcheventcount_' + eventstate + ' eventcount=' + str(eventCount[eventstate]) + '|totaleventcount=' + str(totalEventCount) + ' ' + countStatusText + ' ' + extraText)

#updte: {$lt: ISODate("2018-02-27T19:46:00.000Z")

