#! /usr/bin/python

# Nagios check to monitor the number of files opened by a process. 

# Forked from https://bitbucket.org/fabio79ch/check_num_fds/src/master/check_num_fds.py .
# http://exchange.nagios.org/directory/Plugins/Operating-Systems/Linux/check_num_fds/details

# Requires psutil 5.6.1 (or better?).

# Usage:
# check_num_fds.py -w 1000 -c 2000
# OK: bad pids: dict_values([])

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
  try:
    num_fds = psutil.Process( pid ).num_fds()
# don't need to worry about a PID that's gone, just ignore it
  except (psutil.NoSuchProcess):
    pass

  return num_fds

####

assert options.warn_value > 0
assert options.crit_value > options.warn_value


bad_pids = dict()
status = 0

for pid in (psutil.pids()):
  try:
    num_fds=check_pid(pid)
# don't need to worry about a PID that's gone, just ignore it
  except (psutil.NoSuchProcess):
    continue
  if num_fds > options.crit_value:
    bad_pids[pid] = {'pid':pid,'num_fds':num_fds}
    status = 2
  elif num_fds > options.warn_value:
    bad_pids[pid] = {'pid':pid,'num_fds':num_fds}
    if status == 0: status = 1

# Nagios possible states
status_dict= {0:"OK",1:"WARNING",2:"CRITICAL",3:"UNKNOWN"}

print ("{}: bad pids: ".format(status_dict[status]) + str(bad_pids.values() ) )
#  print ("{0}: Process {1} has {2} file descriptors opened|num_fds={2};{3};{4};;".format(status_dict[status], str( pid ), str( num_fds ), str(options.warn_value), str(options.crit_value) ) )

exit(status)
