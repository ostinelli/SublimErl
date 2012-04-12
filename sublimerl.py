# ==========================================================================================================
# SublimErl - A Sublime Text 2 Plugin for Erlang TDD
# 
# Copyright (C) 2012, Roberto Ostinelli <roberto@ostinelli.net>.
# All rights reserved.
#
# BSD License
# 
# Redistribution and use in source and binary forms, with or without modification, are permitted provided
# that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this list of conditions and the
#	 following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
#	 the following disclaimer in the documentation and/or other materials provided with the distribution.
#  * Neither the name of the authors nor the names of its contributors may be used to endorse or promote
#	 products derived from this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
# WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
# PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
# TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
# HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
# NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.
# ==========================================================================================================

import sublime, sublime_plugin
import sys, os, re, subprocess, threading, webbrowser

SUBLIMERL_VERSION = '0.1'


# core launcher & panel
class SublimErlLauncher():

	def __init__(self, view):
		# init
		self.panel_name = 'sublimerl'
		self.panel_buffer = ''
		self.view = view
		self.window = view.window()
		self.rebar_path = None
		self.erl_path = None
		self.env = None
		# setup
		self.panel = self.window.get_output_panel(self.panel_name)
		self.available = False
		self.setup()

	def update_panel(self):
		if len(self.panel_buffer):
			panel_edit = self.panel.begin_edit()
			self.panel.insert(panel_edit, self.panel.size(), self.panel_buffer)
			self.panel.end_edit(panel_edit)
			self.panel.show(self.panel.size())
			self.panel_buffer = ''
			self.window.run_command("show_panel", {"panel": "output.%s" % self.panel_name})

	def log(self, text):
		self.panel_buffer += text
		sublime.set_timeout(self.update_panel, 0)

	def log_error(self, error_text):
		self.log("Error => %s\n[ABORTED]\n" % error_text)

	def setup(self):
		# is this a .erl file?
		if not self.view.is_scratch():
			if os.path.splitext(self.view.file_name())[1] != '.erl':
				return

		# get module and module_tests filename
		erlang_module_name = self.get_erlang_module_name()
		if erlang_module_name == None: return

		# file saved?
		if self.view.is_scratch():
			self.log_error("This code has not been saved on disk.")
			return

		# set environment
		self.set_env()

		# set cwd to project's root path - so that rebar can access it
		if self.set_cwd_to_otp_project_root() == False:
			self.log_error("This code does not seem to be part of an OTP compilant project.")
			return

		# rebar check
		self.get_rebar_path()
		print self.rebar_path
		if self.rebar_path == None:
			self.log_error("Rebar cannot be found, please download and install from <https://github.com/basho/rebar>.")
			return

		# erl check
		self.get_erl_path()
		if self.erl_path == None:
			self.log_error("Erlang binary (erl) cannot be found.")
			return

		# ok we can use this launcher
		self.available = True

	def set_env(self):
		# TODO: find real path variables
		self.env = os.environ
		self.env['PATH'] = os.environ['PATH'] + ':/usr/local/bin'

	def get_erlang_module_name(self):
		# find module declaration and get module name
		module_region = self.view.find(r"^\s*-\s*module\s*\(\s*(?:[a-zA-Z0-9_]+)\s*\)\s*\.", 0)
		if module_region != None:
			m = re.match(r"^\s*-\s*module\s*\(\s*([a-zA-Z0-9_]+)\s*\)\s*\.", self.view.substr(module_region))
			return m.group(1)


	def set_cwd_to_otp_project_root(self):
		# get otp directory
		current_file_path = os.path.dirname(self.view.file_name())
		otp_project_root = self.get_otp_project_root(current_file_path)

		if otp_project_root == None: return False

		# set current directory to root - needed by rebar
		os.chdir(os.path.abspath(otp_project_root))


	def get_otp_project_root(self, current_dir):
		# if compliant, return
		if self.is_otp_compliant_dir(current_dir) == True: return current_dir
		# if went up to root, stop and return False
		current_dir_split = current_dir.split(os.sep)
		if len(current_dir_split) < 2: return
		# walk up directory
		current_dir_split.pop()
		return self.get_otp_project_root(os.sep.join(current_dir_split))

	def is_otp_compliant_dir(self, directory_path):
		return os.path.exists(os.path.join(directory_path, 'src'))

	def get_rebar_path(self):
		retcode, data = self.execute_os_command('which rebar', block=True)
		data = data.strip()
		if retcode == 0 and len(data) > 0:
			self.rebar_path = data

	def get_erl_path(self):
		retcode, data = self.execute_os_command('which erl', block=True)
		data = data.strip()
		if retcode == 0 and len(data) > 0:
			self.erl_path = data

	def execute_os_command(self, os_cmd, block=False):
		p = subprocess.Popen(os_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=self.set_env())
		if block == True:
			stdout, stderr = p.communicate()
			return (p.returncode, stdout)
		else:
			stdout = []
			for line in p.stdout:
				self.log(line)
				stdout.append("%s\n" % line)
			return (p.returncode, ''.join(stdout))


# start new test
class SublimErlCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		launcher = SublimErlLauncher(self.view)
		if not launcher.available == True: return



