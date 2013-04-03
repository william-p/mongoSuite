#!/usr/bin/env python
# coding: utf-8

import logging
import time

from pymongo import Connection
from Tools import get_config, tcp_ping, str_state, cprint, str_blue

class ReplSet(object):
	def __init__(self, main_config, name, instances, logger_level=logging.INFO):
		self.logger = logging.getLogger('replSet-%s' % name)
		self.logger.setLevel(logger_level)

		self.main_config = main_config
		self.name = name

		default_config = {
			'members': [],
			'arbiters': [],
		}

		self.config = get_config(main_config, 'replSet-%s' % name, default_config)

		members = self.config['members']
		if members:
			members = members.split(",")
			members = [member.replace(" ","") for member in members]

		arbiters = self.config['arbiters']
		if arbiters:
			arbiters = arbiters.split(",")
			arbiters = [arbiter.replace(" ","") for arbiter in arbiters]

		self.members = members
		self.arbiters = arbiters

		self.logger.debug(" + Members: %s" %  members)
		self.logger.debug(" + Arbiters: %s" % arbiters)

		self.instances = []

		for member in members:
			if member in instances.keys():
				instances[member].replSet = self
				self.instances.append(instances[member])
			else:
				self.logger.warning("Instance '%s' not found" % member)

		#self.logger.debug('Config: %s' % self.config)

	def start(self):
		print("Start replica set %s:" % str_blue(self.name))
		for instance in self.instances:
			instance.start()	

	def stop(self):
		print("Stop replica set %s:" % str_blue(self.name))
		for instance in self.instances:
			instance.stop()	

	def get_state(self):
		state = True

		for instance in self.instances:
			state &= instance.get_state()

		return state

	def init(self):
		state = True
		print("Check members of replica set %s:" % str_blue(self.name))

		# Connect to instances
		print("Connect to all instances:")
		for instance in self.instances:
			connected = instance.connect()
			cprint(" + %s:" % instance.name, str_state(connected))
			state &= bool(connected)
		
		if not state:
			self.logger.error("Impossible to init, could not connect to member(s)")
			return False

		print("Check all instances setName:")
		for instance in self.instances:
			setName = not bool(instance.setName)
			cprint(" + %s:" % instance.name, str_state(setName, nok=instance.setName))
			state &= setName 

		if not state:
			self.logger.error("Impossible to init, replica set already configured")
			return False
		

		replSet_cfg = {
			'_id': self.name,
			'members': []
		}

		for index, instance in enumerate(self.instances):
			cfg = {
				'_id': index,
				 'host': "%s:%s" % (instance.node.config["host"], instance.config["port"])
			}
			if instance.name in self.arbiters:
				cfg['arbiterOnly'] = True

			replSet_cfg['members'].append(cfg)

		self.logger.debug("replSet config: %s" % replSet_cfg)

		master = self.instances[0]

		print("Init replica set %s on %s" % (str_blue(self.name), str_blue(instance.name)))
		master.mclient.admin.command("replSetInitiate", replSet_cfg)

		print("Waiting configuration propagation:")
		for instance in self.instances:
			# Wait
			for i in range(10):
				info = instance.mclient["admin"].command("isMaster")
				if info.get('setName', None) == self.name:
					break
				time.sleep(1)

			cprint(" + %s:" % instance.name, str_state(state))

		print("Waiting master instance:")
		masters = []

		for i in range(20):
			for instance in self.instances:
				info = instance.mclient["admin"].command("isMaster")
				if info.get('ismaster', False):
					master = instance.name
					break
			
			time.sleep(1)

		cprint(" + Master:", str_state(master, ok=master, nok="Unknown"))

		if master:
			print("%s ready for actions." % str_blue(self.name))
		else:
			self.logger.warning("Waiting timeout, initialization maybe is too long ... You can check status with 'status' command.")

	def status(self):
		state = self.get_state()
		masters = []
		primaries = []
		secondaries = []
		arbiters = []

		print("State of " + str_blue(self.name) + ": " + str_state(state))
		cprint(" + Instances:", len(self.instances))
		for instance in self.instances:
			if instance.connected:
				if instance.isMaster:
					masters.append(instance.name)
				if instance.isPrimary:
					primaries.append(instance.name)
				if instance.isSecondary:
					secondaries.append(instance.name)
				if instance.isArbiter:
					arbiters.append(instance.name)

			cprint("   - %s (%s):" % (instance.name, instance.me), str_state(instance.state))

		cprint(" + Masters:",		str_state(len(masters),		ok=", ".join(masters), nok="Unknown"))

		if self.arbiters:
			cprint(" + Arbiters:",		str_state(len(arbiters),	ok=", ".join(arbiters), nok="Unknown"))
			
		cprint(" + Primaries:",		str_state(len(primaries), 	ok=", ".join(primaries), nok="Unknown"))
		cprint(" + Secondaries:",	str_state(len(secondaries),	ok=", ".join(secondaries), nok="Unknown"))

	def __del__(self):
		pass