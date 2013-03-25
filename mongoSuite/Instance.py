#!/usr/bin/env python
# coding: utf-8

import logging
import time

from pymongo import Connection
from Tools import get_config, tcp_ping, str_state, cprint, str_blue

class Instance(object):
	def __init__(self, main_config, node, name, logger_level=logging.INFO):
		self.logger = logging.getLogger('instance-%s' % name)
		self.logger.setLevel(logger_level)

		self.main_config = main_config
		self.name = name

		self.node = node

		mongod_bin = 	 node.config['mongod_bin']
		mongod_dbpath =  "%s/%s/" %    (node.config['mongod_dbpath'], name) 
		mongod_logpath = "%s/%s.log" % (node.config['mongod_logpath'], name) 
		mongod_pidpath = "%s/%s.pid" % (node.config['mongod_pidpath'], name) 

		default_config = {
			'flags': None,
			'port': 27017,
			'mongod_bin': mongod_bin,
			'mongod_logpath': mongod_logpath,
			'mongod_pidpath': mongod_pidpath,
			'mongod_dbpath': mongod_dbpath,
			'managed': True
		}
		
		self.pid = None

		self.config = get_config(main_config, 'instance-%s' % name, default_config)

		self.logger.debug('Config: %s' % self.config)

		self.connected = False
		self.mclient = None
		self.minfo = None

	def make_cmd(self):
		cmd = self.config['mongod_bin']

		cmd += " --logpath %s" % self.config['mongod_logpath']
		cmd += " --dbpath %s" % self.config['mongod_dbpath']
		cmd += " --pidfilepath %s" % self.config['mongod_pidpath']
		cmd += " --port %s" % self.config['port']

		if self.config['flags']:
			cmd += " %s " % self.config['flags']

		cmd += " --fork"

		self.logger.debug('Command line: %s' % cmd)

		return cmd

	def get_pid(self):
		#if self.pid:
		#	return self.pid

		if not self.node.file_exist(self.config['mongod_pidpath']):
			return None

		pid = self.node.exec_command("cat %s | tail -n 1" % self.config['mongod_pidpath'])
		self.logger.debug("Pid: %s" % pid)
		try:
			pid = int(pid)
			return pid
		except:
			return None

	def get_state(self):
		state = True
		self.states = {}

		self.pid = self.get_pid()

		self.states['pid'] = self.pid
		self.states['pid_run'] = False
		self.states['tcp_ping'] = tcp_ping(self.node.config["host"], self.config["port"])

		self.states['lock'] = False

		try:
			lock = self.node.exec_command("cat %s/mongod.lock | tail -n 1" % self.config['mongod_dbpath'])
			if lock and int(lock) == self.pid:
				self.states['lock'] = True
		except:
			pass

		self.states['running'] = self.check_running()

		if self.pid:
			self.states['pid_run'] = self.node.file_exist("/proc/%s/cmdline" % self.pid)

		for key in self.states:
			state &= bool(self.states[key])

		return state

	def check_running(self):
		self.pid = self.get_pid()
		if self.pid:
			return self.node.file_exist("/proc/%s/cmdline" % self.pid)
		else:
			return False
		
	def start(self):
		print("Start " + str_blue(self.name) + " on " + str_blue(self.node.name) + ":")

		if not self.config['managed']:
			print(" + Not managed")
			return True

		self.node.exec_command("mkdir -p %s" % self.config['mongod_dbpath'])

		state = self.check_running()
		if state:
			print(" + Already started")
			return True

		if not self.node.file_exist(self.config['mongod_bin']):
			str_state(False, nok=" + Impossible to find mongod binary")
			return False

		cmd = self.make_cmd()
		self.node.exec_command(cmd)

		for i in range(0, 10):
			state = self.get_state()
			if state:
				print(" + " + str_state(True, ok="Done"))
				return True

			time.sleep(1)

		print(" + " + str_state(False, nok="Fail"))
		print("See '%s' for more informations ..." % self.config['mongod_logpath'])
		return False

	def stop(self):
		print("Stop " + str_blue(self.name) + " on " + str_blue(self.node.name) + ":")

		if not self.config['managed']:
			print(" + Not managed")
			return True

		state = self.check_running()
		if not state:
			print(" + Already stoped")
			return True

		pid = self.get_pid()
		if pid:
			self.node.exec_command("kill %s" % pid)
		else:
			self.logger.warning("Invalid Pid")
			return

		for i in range(0, 10):
			state = self.get_state()
			if not state:
				print(" + " + str_state(True, ok="Done"))
				return True

			time.sleep(1)

		print(" + " + str_state(False, nok="Fail"))
		return False

	def connect(self):
		if not self.connected:
			try:
				self.mclient = Connection(self.node.config['host'], self.config['port'])
				self.minfo = self.mclient.server_info()
				self.connected = True
				return self.minfo

			except Exception as err:
				self.logger.error(err)
				return None

	def disconnect(self):
		if self.connected:
			self.mclient.disconnect()
			self.connected = False

	def status(self):
		state = self.get_state()

		print("State of " + str_blue(self.name) + " on " + str_blue(self.node.name) + ": " + str_state(state))
		cprint(" + Node:",			str_state(self.node.get_state()) )
		cprint(" + Managed:",		str_state(self.config['managed'], ok="Yes", nok="No") )
		cprint(" + Sarted:",		str_state(self.states['running']) )
		cprint(" + Port:",			self.config['port'] )
		cprint(" + TCP Ping:",		str_state(self.states['tcp_ping']) )
		cprint(" + Lock:",		    str_state(self.states['lock']) )

		if self.states['lock']:
			self.connect()
			
		if self.connected:
			cprint(" + PID:",			str_state(self.pid, ok=self.pid) )
			cprint(" + Mongod:", "%s (%s bits, debug: %s)" % (self.minfo.get('version', False), self.minfo.get('bits', ''), self.minfo.get('debug', '')) )
			dbs = self.mclient.database_names()
			cprint(" + DBs:", len(dbs))
			for db in dbs:
				cprint("   - '%s':" % db, "%s Collections" % len(self.mclient[db].collection_names()) )

	def __del__(self):
		self.disconnect()