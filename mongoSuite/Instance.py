#!/usr/bin/env python
# coding: utf-8

import logging
import time
import sys

from pymongo import Connection
from Tools import get_config, tcp_ping, str_state, cprint, str_blue

class Instance(object):
	def __init__(self, main_config, node, name, replSet=None, logger_level=logging.INFO):
		self.logger = logging.getLogger('instance-%s' % name)
		self.logger.setLevel(logger_level)

		self.main_config = main_config
		self.name = name

		self.node = node

		mongo_dbin = 	 node.config['mongo_dbin']
		mongo_dbpath =  "%s/%s/" %    (node.config['mongo_dbpath'], name) 
		mongo_logpath = "%s/%s.log" % (node.config['mongo_logpath'], name) 
		mongo_pidpath = "%s/%s.pid" % (node.config['mongo_pidpath'], name) 

		default_config = {
			'flags': None,
			'port': 27017,
			'mongo_dbin': mongo_dbin,
			'mongo_logpath': mongo_logpath,
			'mongo_pidpath': mongo_pidpath,
			'mongo_dbpath': mongo_dbpath,
			'managed': True,
			'replset': None
		}

		self.config = get_config(main_config, 'instance-%s' % name, default_config)

		#self.logger.debug('Config: %s' % self.config)

		# Set by replicaSet
		self.replSet = replSet

		self.logger.debug('Config replset: %s' % self.config['replset'])

		self.pid = None
		self.connected = False
		self.mclient = None
		self.minfo = None
		self.me = None
		self.isMaster = False
		self.isPrimary = False
		self.isSecondary = False

	def make_cmd(self):
		cmd = self.config['mongo_dbin']

		cmd += " --logpath %s" % self.config['mongo_logpath']
		cmd += " --dbpath %s" % self.config['mongo_dbpath']
		cmd += " --pidfilepath %s" % self.config['mongo_pidpath']
		cmd += " --port %s" % self.config['port']

		if self.replSet:
			cmd += " --replSet %s " % self.replSet.name

		if self.config['flags']:
			cmd += " %s " % self.config['flags']

		cmd += "--logappend --fork"


		self.logger.debug('Command line: %s' % cmd)

		return cmd

	def get_pid(self):
		#if self.pid:
		#	return self.pid

		if not self.node.file_exist(self.config['mongo_pidpath']):
			return None

		pid = self.node.exec_command("cat %s | tail -n 1" % self.config['mongo_pidpath'])
		self.logger.debug("Pid: %s" % pid)
		try:
			pid = int(pid)
			return pid
		except:
			return None

	def ping(self):
		return tcp_ping(self.node.config["host"], self.config["port"])

	def get_state(self):
		state = True
		self.states = {}

		self.pid = self.get_pid()

		self.states['pid'] = self.pid
		self.states['pid_run'] = False
		self.states['tcp_ping'] = self.ping()

		self.states['lock'] = False

		try:
			lock = self.node.exec_command("cat %s/mongod.lock | tail -n 1" % self.config['mongo_dbpath'])
			if lock and int(lock) == self.pid:
				self.states['lock'] = True
		except:
			pass

		self.states['running'] = self.check_running()

		if self.pid:
			self.states['pid_run'] = self.node.file_exist("/proc/%s/cmdline" % self.pid)

		if self.states['lock']:
			self.connect()

		self.states['replSet'] = False
		if self.minfo and self.replSet:
			self.states['replSet'] = self.minfo["isMaster"].get("setName", None) == self.replSet.name

		for key in self.states:
			state &= bool(self.states[key])

		self.state = state
		return state

	def check_running(self):
		self.pid = self.get_pid()

		state = self.ping()

		if state and not self.connected:
			state &= bool(self.connect())
			
		return state
		
	def start(self):
		print("Start " + str_blue(self.name) + " on " + str_blue(self.node.name) + ":")

		if not self.config['managed']:
			print(" + Not managed")
			return True

		self.node.exec_command("mkdir -p %s" % self.config['mongo_dbpath'])

		state = self.check_running()
		if state:
			print(" + Already started")
			return True

		if not self.node.file_exist(self.config['mongo_dbin']):
			str_state(False, nok=" + Impossible to find mongod binary")
			return False

		cmd = self.make_cmd()
		self.node.exec_command(cmd)

		for i in range(0, 10):
			state = self.check_running()
			if state:
				print(" + " + str_state(True, ok="Done"))
				return True

			time.sleep(1)

		print(" + " + str_state(False, nok="Fail"))
		print("See '%s' for more informations ..." % self.config['mongo_logpath'])
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
			state = self.check_running()
			if not state:
				print(" + " + str_state(True, ok="Done"))
				return True

			time.sleep(1)

		print(" + " + str_state(False, nok="Fail"))
		return False

	def reset(self, prompt=True):
		print("Reset " + str_blue(self.name) + " on " + str_blue(self.node.name) + ":")

		do = True

		if prompt:
			do = False
			try:
				choice = raw_input('Warning, this operation erase all your DB data, are you sure ? (yes/no): ')
			except:
				print('')
				sys.exit(1)

			if choice == "yes":
				do = True
		
		if not do:
			return

		self.node.exec_command("rm -Rf %s" % self.config['mongo_dbpath'])
		self.node.exec_command("rm %s" % self.config['mongo_pidpath'])
		self.node.exec_command("rm %s" % self.config['mongo_logpath'])
		self.node.exec_command("rm %s.*" % self.config['mongo_logpath'])

		print(" + " + str_state(True, ok="Done"))
		return True

	def connect(self):
		if not self.connected:
			try:
				self.mclient = Connection(self.node.config['host'], self.config['port'], slaveOk=True)
				self.minfo = self.mclient.server_info()
				self.connected = True

				self.minfo['isMaster'] = self.mclient["admin"].command("isMaster")

				self.logger.debug("info: %s" % self.minfo)
				self.logger.debug("isMaster: %s" % self.minfo['isMaster'])

				self.me = 		self.minfo['isMaster'].get("me", None)
				self.setName =	self.minfo['isMaster'].get("setName", None)
				self.isMaster = self.minfo['isMaster'].get("ismaster", False)
				self.isArbiter = self.me in self.minfo['isMaster'].get("arbiters", [])

				self.isPrimary = self.me == self.minfo['isMaster'].get("primary", 'noOne')

				self.isSecondary = self.minfo['isMaster'].get("secondary", False)

				return self.minfo

			except Exception as err:
				self.logger.error(err)
				return None

	def disconnect(self):
		if self.connected:
			self.mclient.disconnect()
			self.connected = False

	def replSet_addMember(self, member):
		print("Add member " + str_blue(member.name) + " on " + str_blue(self.replSet.name) )
		#rs.add("wpain-laptop:2002")
		#self.mclient.admin.command("rs.add('wpain-laptop:20000')")

	def status(self):
		state = self.get_state()

		print("State of " + str_blue(self.name) + " on " + str_blue(self.node.name) + ": " + str_state(state))
		cprint(" + Node:",			str_state(self.node.get_state()) )
		cprint(" + Managed:",		str_state(self.config['managed'], ok="Yes", nok="No") )
		cprint(" + Sarted:",		str_state(self.states['running'], ok="Yes", nok="No") )
		cprint(" + Port:",			self.config['port'] )
		cprint(" + TCP Ping:",		str_state(self.states['tcp_ping']) )
		cprint(" + Lock:",		    str_state(self.states['lock']) )
		
		if self.connected:
			cprint(" + replset:",		str_state(self.states['replSet'], ok="Yes", nok="No"))

			cprint(" + PID:",			str_state(self.pid, ok=self.pid) )
			cprint(" + Mongod:", "%s (%s bits, debug: %s)" % (self.minfo.get('version', False), self.minfo.get('bits', ''), self.minfo.get('debug', '')) )
			
			isMaster = self.minfo.get("isMaster", None)

			isreplicaset =	isMaster.get("isreplicaset", False)
			hosts =			isMaster.get("hosts", [])
			arbiters =		isMaster.get("arbiters", [])

			if self.setName:
				cprint(" + setName:",	str_state(self.setName==self.replSet.name, ok=self.setName, nok=self.setName))
				cprint(" + Me:",		self.me)
				cprint(" + Master:",	str_state(self.isMaster,	ok="Yes", nok="No"))
				cprint(" + Primary:",	str_state(self.isPrimary,	ok="Yes", nok="No"))
				cprint(" + Secondary:",	str_state(self.isSecondary,	ok="Yes", nok="No"))
				cprint(" + Arbiter:",	str_state(self.isArbiter,	ok="Yes", nok="No"))
				cprint(" + Arbiters:",	arbiters)
				cprint(" + Members:",	hosts)

			"""
			if not self.isPrimary and not self.isSecondary:
				return

			dbs = self.mclient.database_names()
			cprint(" + DBs:", len(dbs))

			for db in dbs:
				cprint("   - '%s':" % db, "%s Collections" % len(self.mclient[db].collection_names()) )
			"""

	def __del__(self):
		self.disconnect()