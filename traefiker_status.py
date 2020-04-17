import requests
import configparser
import argparse
import json

parser = argparse.ArgumentParser(description='Query Traefiker narrative_status/ and report state.')
parser.add_argument('--config-file', dest='configfile', required=True,
		    help='Path to config file (INI format). (required)')
parser.add_argument('--config-sections', dest='sections', nargs='*',
		    help='Section(s) in config file to use. (default to all sections in config file)')
args = parser.parse_args()

configfile=args.configfile
conf=configparser.ConfigParser()
conf.read(configfile)
#print (conf.sections())

# skip to end for loop that processes each section

def process_section(conf, section):

	status_strings = ['OK','WARNING','CRITICAL','UNKNOWN']

	# valid states we expect from traefiker
	container_states = ['active','queued']

	url=conf[section]['traefiker_status_url']
	token=conf[section]['kbase_token']

	counts = { 'total': 0 }
	warn = {  }
	crit = {  }
	status = { }
	for state in container_states:
		counts[state]=0
		warn[state] = int(conf[section][state+'_warn'])
		crit[state] = int(conf[section][state+'_crit'])
		status[state] = 3

	cookies = dict()
	cookies['kbase_session'] = token

	req = requests.get(url , cookies=cookies)
	if req.status_code != 200:
		print('bad response')
		return 2

	sessions = {}
	for narrative in req.json()['narrative_services']:
		counts['total'] += 1
		try:
			counts[narrative['state']] += 1
		except:
			# bad state from traefiker, not handled yet
			pass

# this code in theory looks for users with multiple containers
# but the status endpoint 500s in that situation anyway
#		if narrative['session_id'] != '*':
#			if sessions.has_key(narrative['session_id']):
#				print (session_id)
#			sessions[narrative['session_id']] = 1

	for state in container_states:
		if counts[state] > crit[state]:
			status[state] = 2
		if counts[state] > warn[state]:
			status[state] = 1
		else:
			status[state] = 0
# want performance data here but not required
		print (str(status[state]) + ' traefiker_' + section + '_' + state + ' - ' + status_strings[status[state]] + ' hi ' )


#	print (counts)
#	print (warn)
#	print (crit)
#	print (status)

# main loop
# if args provided, use them, otherwise use sections from config file
if args.sections:
	sections = args.sections
else:
	sections = conf.sections()

for section in sections:
#	print (section)
	process_section(conf, section)
