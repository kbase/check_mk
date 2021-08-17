#! /usr/bin/python

# Nagios check to monitor the number of files opened by a process. 

# Forked from https://bitbucket.org/fabio79ch/check_num_fds/src/master/check_num_fds.py .

# psutil in Python3 does not seem to support num_fds, which is pretty important.
# So we'll leave this as Python2 for now.

# Usage:
# check_num_fds.py -p -f /var/run/mydaemon.pid 
# OK: Process 13403 has 4037 file descriptors opened|num_fds=4037;6000;6000;;

# http://exchange.nagios.org/directory/Plugins/Operating-Systems/Linux/check_num_fds/details

try:
    import psutil
except ImportError:
    fail("You need the psutil python module")
    
import optparse

usage = """

%prog -w 1024 -c 2048
"""

parser = optparse.OptionParser(usage=usage)
parser.add_option("-v", "--verbose" , action="store_true" , dest="verbose" , help="verbose mode.")

parser.add_option("-w", "--warn",     dest="warn_value",   default="-1",     type="int", help="warning threshold.")
parser.add_option("-c", "--crit",     dest="crit_value",   default="-1",     type="int", help="critical threshold.")

(options, args) = parser.parse_args()

if len(args) != 0:
    fail( parser.print_help() )

import os
import sys
import pprint

def check_pid(pid):
# Getting the number of files opened by pid
  num_fds = psutil.Process( pid ).num_fds()

  return num_fds

bad_pids = dict()

assert options.warn_value > 0
assert options.crit_value > 0

# Nagios possible states
status_dict= {0:"OK",1:"WARNING",2:"CRITICAL",3:"UNKNOWN"}

status = 0
for pid in (psutil.pids()):
  num_fds=check_pid(pid)
  if num_fds > options.crit_value:
    bad_pids[pid] = num_fds
    status = 2
  elif num_fds > options.warn_value:
    bad_pids[pid] = num_fds
    if status == 0: status = 1

pprint.pprint ("{}: ".format(status_dict[status]) + str(bad_pids) )
#  print ("{0}: Process {1} has {2} file descriptors opened|num_fds={2};{3};{4};;".format(status_dict[status], str( pid ), str( num_fds ), str(options.warn_value), str(options.crit_value) ) )

exit(status)
