#!/usr/bin/env python
# coding: utf-8

import socket

def create_default_config(path):
	config = """
[mongoSuite]
mongo_binpath =  ~/mongoSuite/bin
mongo_dbpath =   ~/mongoSuite/data
mongo_logpath =  ~/mongoSuite/log
mongo_pidpath =  ~/mongoSuite/run
mongo_dbin =     ~/mongoSuite/bin/mongod
mongo_sbin =     ~/mongoSuite/bin/mongos
mongo_shell =    ~/mongoSuite/bin/mongo
ssh_pkey =       ~/.ssh/id_rsa
timeout =        1

[node-Node1]
host = localhost

#[node-Node2]
#host = 127.0.0.1
#ssh_user = 	mongosuite
#mongo_dbin =   ~/bin/mongod
#mongo_shell =  ~/bin/mongo

[instance-MyDB1]
node = Node1
port = 20001
flags = --nojournal --noprealloc

[instance-MyDB2]
node = Node1
port = 20002
flags = --nojournal --noprealloc

[instance-MyDB3]
node = Node1
port = 20003
flags = --nojournal --noprealloc

[replSet-rs_test]
members = MyDB1, MyDB2, MyDB3
#arbiters = MyDB3
	"""

	conf_file = open(path, 'w')
	conf_file.write(config)
	conf_file.close()


def tcp_ping(host, port, timeout=0.5):
	ping = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
	ping.settimeout(timeout)
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
		if space <= 0:
			space = 1

		print(col1 + " "*space + col2)