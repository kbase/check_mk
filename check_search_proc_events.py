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

warnInterval=3600 * 1
critInterval=3600 * 2
warnAgo=datetime.datetime.fromtimestamp(time.time() - warnInterval, pytz.timezone("US/Pacific"))
critAgo=datetime.datetime.fromtimestamp(time.time() - critInterval, pytz.timezone("US/Pacific"))

client=MongoClient(hostname)
db=client.search
db.authenticate(username,password)
events=db.searchEvents

status = 3
statusText = 'UNKNOWN'
extraText = 'unknown state'

warnCount = events.find({"status":"PROC","updte": {"$lt": warnAgo}}).count()
critCount = events.find({"status":"PROC","updte": {"$lt": critAgo}}).count()
if (warnCount == 0):
  status = 0
  statusText = 'OK'
  extraText = 'no events found older than ' + str(warnInterval) + ' seconds'
if (warnCount > 0):
  status = 1
  statusText = 'WARNING'
  extraText = str(warnCount) + ' events found older than ' + str(warnInterval) + ' seconds'
if (critCount > 0):
  status = 2
  statusText = 'CRITICAL'
  extraText = str(critCount) + ' events found older than ' + str(critInterval) + ' seconds'

#print events.find({"status":"PROC"}).count()
#updte: {$lt: ISODate("2018-02-27T19:46:00.000Z")

print str(status) + ' searcheventage' + ' - ' + statusText + ' ' + extraText
