#!/usr/bin/env python
# coding: utf-8

import logging
import paramiko
import subprocess
import os

from Tools import tcp_ping, get_config, str_state, cprint, str_blue

class Node(object):
	def __init__(self, main_config, name, logger_level=logging.INFO):
		self.logger = logging.getLogger('node-%s' % name)
		self.logger.setLevel(logger_level)

		self.main_config = main_config
		self.name = name

		mongod_binpath = main_config.get("mongoSuite", "mongod_binpath")
		mongod_dbpath =  main_config.get("mongoSuite", "mongod_dbpath")
		mongod_logpath = main_config.get("mongoSuite", "mongod_logpath")
		mongod_pidpath = main_config.get("mongoSuite", "mongod_pidpath")

		mongod_bin = 	 main_config.get("mongoSuite", "mongod_bin")
		mongod_shell =   main_config.get("mongoSuite", "mongod_shell")

		default_config = {
			'host': 'localhost',
			'ssh_user': os.environ['USER'],
			'ssh_port': 22,
			'ssh_pkey': main_config.get("mongoSuite", "ssh_pkey"),
			'mongod_shell': mongod_shell,
			'mongod_bin': mongod_bin,
			'mongod_binpath': mongod_binpath,
			'mongod_dbpath': mongod_dbpath,
			'mongod_logpath': mongod_logpath,
			'mongod_pidpath': mongod_pidpath
		}
		
		self.config = get_config(main_config, 'node-%s' % name,default_config)

		self.config['ssh_pkey'] = os.path.expanduser(self.config['ssh_pkey'])

		self.connected = False
		self.ssh_client = None
		self.ssh_error = False
		self.home_dir = None
		self.states = {}

		self.logger.debug('Config: %s' % self.config)

	def connect(self):
		if self.ssh_error:
			return False

		if self.config['host'] == 'localhost':
			self.make_env()
			self.connected = True
			return True

		self.ssh_client = paramiko.SSHClient()
		self.ssh_client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
		self.logger.debug("Connect to ssh:")
		try:
			self.ssh_client.connect(
				self.config['host'],
				port=self.config['ssh_port'],
				username=self.config['ssh_user'],
				timeout=5,
				key_filename=self.config['ssh_pkey'])

			self.connected = True
			self.logger.debug(" + Done")

			self.make_env()
			return True

		except Exception as err:
			self.logger.debug(" + Fail")
			self.ssh_error = True
			self.logger.error("Impossible to connect to %s@%s:%s: %s" % (
				self.config['ssh_user'],
				self.config['host'],
				self.config['ssh_port'],
				err))
			return False

	def disconnect(self):
		if self.connected and self.ssh_client:
			self.logger.debug("Disconnect from ssh")
			self.ssh_client.close()

	def expanduser(self, path):
		if self.config['host'] == 'localhost':
			return os.path.expanduser(path)
		else:
			return path.replace('~', self.home_dir)

	def make_env(self):
		self.logger.debug("Make Environment:")	

		self.home_dir = self.exec_command("echo $HOME")

		# Expand User
		for key in ['mongod_shell', 'mongod_bin', 'mongod_binpath', 'mongod_dbpath', 'mongod_logpath', 'mongod_pidpath']:
			self.config[key] = self.expanduser(self.config[key])

		self.logger.debug(" + %s" % self.config['mongod_binpath'])
		self.exec_command("mkdir -p %s" % self.config['mongod_binpath'])

		self.logger.debug(" + %s" % self.config['mongod_dbpath'])
		self.exec_command("mkdir -p %s" % self.config['mongod_dbpath'])

		self.logger.debug(" + %s" % self.config['mongod_logpath'])
		self.exec_command("mkdir -p %s" % self.config['mongod_logpath'])

		self.logger.debug(" + %s" % self.config['mongod_pidpath'])
		self.exec_command("mkdir -p %s" % self.config['mongod_pidpath'])

	def exec_command(self, command):

		self.logger.debug("Exec_command \"%s\"" % command)

		stdout, stderr = None, None

		if self.config['host'] == 'localhost':
			# use local shell

			p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=256*1024*1024, shell=True)
			
			stdout, stderr = p.communicate()
			code = p.returncode

			self.logger.debug("Code: %s" % code)

		else:
			# use remove shell via SSH
			if not self.connected:
				self.connect()

			if self.connected:
				(stdin, stdout, stderr) = self.ssh_client.exec_command(command, bufsize=-1)
				stdout = stdout.read()
				stderr = stderr.read()

		# Remove '\n'
		if stdout and stdout[len(stdout)-1] == '\n':
			stdout = stdout[:len(stdout)-1]
		# Remove '\n'
		if stderr and stderr[len(stderr)-1] == '\n':
			stderr = stderr[:len(stderr)-1]

		if stderr:
			self.logger.debug("stderr: \"%s\"" % stderr)

		if stdout:
			self.logger.debug("stdout: \"%s\"" % stdout)
			return stdout

		return None


	def file_exist(self, path):
		output = self.exec_command("stat %s | tail -n 1" % path)
		if output:
			return True
		else:
			return False

	def get_state(self):
		state = True
		self.states = {}

		if not self.connected:
			self.connect()

		self.states['ssh'] = self.connected
		self.states['mongod_bin'] = self.file_exist(self.config['mongod_bin'])
		self.states['mongod_shell'] = self.file_exist(self.config['mongod_shell'])

		for key in self.states:
			state &= bool(self.states[key])

		return state

	def status(self):
		state = self.get_state()

		print("State of " + str_blue(self.name) +  " on %s@%s:%s" % (self.config['ssh_user'], self.config['host'], self.config['ssh_port']) + ": " + str_state(state))

		if not self.config['host'] == 'localhost':
			cprint(" + Ssh:", str_state(self.states['ssh'], ok="Online", nok="Offline"))

		cprint(" + Mongod Binary:",	str_state(self.states['mongod_bin']) )
		cprint(" + Mongod Shell:",	str_state(self.states['mongod_shell']) )

		if self.connected:
			cprint(" + OS:", self.exec_command('uname -a'))
			#print " + Cores: %s" % self.exec_command('cat /proc/cpuinfo | grep "processor" | wc -l')

	def __del__(self):
		self.disconnect()