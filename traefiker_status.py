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

	# valid states we expect from traefiker
	container_states = ['active','queued']

	url=conf[section]['traefiker_status_url']
	token=conf[section]['kbase_token']

	counts = { 'total': 0 }
	warns = { 'total': 0 }
	crit = { 'total': 0 }
	for state in container_states:
		counts[state]=0
		warn[state] = conf[section][state+'_warn']
		crit[state] = conf[section][state+'_crit']

	cookies = dict()
	cookies['kbase_session'] = token

	req = requests.get(url , cookies=cookies)

	for narrative in req.json()['narrative_services']:
		counts['total'] += 1
		try:
			counts[narrative['state']] += 1
		except:
			# bad state from traefiker, not handled yet
			pass

	print (counts)
	print (warn)
	print (crit)

# main loop
# if args provided, use them, otherwise use sections from config file
if args.sections:
	sections = args.sections
else:
	sections = conf.sections()

for section in sections:
#	print (section)
	process_section(conf, section)
