#!/usr/bin/env python
# coding: utf-8

import socket

def create_default_config(path):
	config = """
[mongoSuite]
mongod_binpath = ~/mongoSuite/bin
mongod_dbpath =  ~/mongoSuite/data
mongod_logpath = ~/mongoSuite/log
mongod_pidpath = ~/mongoSuite/run
mongod_bin =     ~/mongoSuite/bin/mongod
mongod_shell =   ~/mongoSuite/bin/mongo
ssh_pkey =       ~/.ssh/id_rsa

[node-Node1]
host = localhost

[node-Node2]
host = localhost

#[node-Node3]
#host = 127.0.0.1
#ssh_user = mongosuite
#mongod_bin =     ~/bin/mongod
#mongod_shell =   ~/bin/mongo

#[instance-Mongosuite]
#node = Node3
#port = 27017
#mongod_dbpath =  ~/var/lib/mongodb/

[instance-Arbiter]
node = Node1
port = 20000
flags = --nojournal --noprealloc

[instance-MyDB1]
node = Node1
port = 20001
flags = --nojournal --noprealloc

[instance-MyDB2]
node = Node2
port = 20002
flags = --nojournal --noprealloc
	"""

	conf_file = open(path, 'w')
	conf_file.write(config)
	conf_file.close()


def tcp_ping(host, port):
	ping = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	ping.settimeout(0.5)
	try:
        	ping.connect((host, int(port)))
		ping.close()
		return True
	except socket.error:
		return False

def config_get(config, section, field, default):
	try:
		return config.get(section ,field)
	except:
		return default


def get_config(main_config, section, default):
	items = main_config.items(section)

	config = {}

	for key, value in items:
		
		if value.lower() == "true":
			value = True
		elif value.lower() == "false":
			value = False

		try:
			value = int(value)
		except:
			pass

		config[key] = value

	# Merge dict
	for key in default:
		config[key] = config.get(key,  default[key])

	return config


def str_state(state, ok="Ok", nok="Nok"):
	end_color = '\033[0m'
	ok_color = '\033[92m'
	nok_color = '\033[91m'

	if state:
		return "%s%s%s" % (ok_color, ok, end_color)
	else:
		return "%s%s%s" % (nok_color, nok, end_color)

def str_blue(mystr):
	color = '\033[94m'
	return "%s%s\033[0m" % (color, mystr)


def cprint(col1, col2=None, colchar=20):
	if not col2:
		print(col1)
	else:
		col1 = str(col1)
		col2 = str(col2)
		space = colchar - len(col1)
		print(col1 + " "*space + col2)