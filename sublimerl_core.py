# ==========================================================================================================
# SublimErl - A Sublime Text 2 Plugin for Erlang Integrated Testing & Code Completion
#
# Copyright (C) 2013, Roberto Ostinelli <roberto@ostinelli.net>.
# All rights reserved.
#
# BSD License
#
# Redistribution and use in source and binary forms, with or without modification, are permitted provided
# that the following conditions are met:
#
#  * Redistributions of source code must retain the above copyright notice, this list of conditions and the
#        following disclaimer.
#  * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
#        the following disclaimer in the documentation and/or other materials provided with the distribution.
#  * Neither the name of the authors nor the names of its contributors may be used to endorse or promote
#        products derived from this software without specific prior written permission.
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

# globals
SUBLIMERL_VERSION = '0.5.1'

# imports
import sublime, sublime_plugin
import os, subprocess, re

# plugin initialized (Sublime might need to be restarted if some env configs / preferences change)
class SublimErlGlobal():

	def __init__(self):
		# default
		self.initialized = False
		self.init_errors = []

		self.plugin_path = None
		self.completions_path = None
		self.support_path = None

		self.erl_path = None
		self.escript_path = None
		self.rebar_path = None
		self.dialyzer_path = None
		self.erlang_libs_path = None

		self.last_test = None
		self.last_test_type = None
		self.test_in_progress = False

		self.env = None
		self.settings = None
		self.completion_skip_erlang_libs = None

		# initialize
		self.set_settings()
		self.set_env()
		self.set_completion_skip_erlang_libs()

		if self.set_paths() == True and self.set_erlang_libs_path() == True:
			# available
			self.initialized = True

	def set_settings(self):
		self.settings = sublime.load_settings('SublimErl.sublime-settings')

	def set_env(self):
		# TODO: enhance the finding of paths
		self.env = os.environ.copy()
		if sublime.platform() == 'osx':
			# get relevant file paths
			etc_paths = ['/etc/paths']
			for f in os.listdir('/etc/paths.d'):
				etc_paths.append(os.path.join('/etc/paths.d', f))
			# bash profile
			bash_profile_path = os.path.join(os.getenv('HOME'), '.bash_profile')
			# get env paths
			additional_paths = "%s:%s" % (self._readfiles_one_path_per_line(etc_paths), self._readfiles_exported_paths([bash_profile_path]))
			# add
			self.env['PATH'] = self.env['PATH'] + additional_paths

	def _readfiles_one_path_per_line(self, file_paths):
		concatenated_paths = []
		for file_path in file_paths:
			if os.path.exists(file_path):
				f = open(file_path, 'r')
				paths = f.read()
				f.close()
				paths = paths.split('\n')
				for path in paths:
					concatenated_paths.append(path.strip())
		return ':'.join(concatenated_paths)

	def _readfiles_exported_paths(self, file_paths):
		concatenated_paths = []
		for file_path in file_paths:
			if os.path.exists(file_path):
				p = subprocess.Popen(". %s; echo $PATH" % file_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				path, stderr = p.communicate()
				concatenated_paths.append(path.strip())
		return ''.join(concatenated_paths)

	def set_paths(self):

		def log(message):
			self.init_errors.append(message)
			print "SublimErl Init Error: %s" % message

		def test_path(path):
			return path != None and os.path.exists(path)

		# erl check
		self.erl_path = self.settings.get('erl_path', self.get_exe_path('erl'))
		if test_path(self.erl_path) == False:
			log("Erlang binary (erl) cannot be found.")

		# escript check
		self.escript_path = self.settings.get('escript_path', self.get_exe_path('escript'))
		if test_path(self.escript_path) == False:
			log("Erlang binary (escript) cannot be found.")

		# rebar
		self.rebar_path = self.settings.get('rebar_path', self.get_exe_path('rebar'))
		if test_path(self.rebar_path) == False:
			log("Rebar cannot be found, please download and install from <https://github.com/basho/rebar>.")
			return False
			return False

		# dialyzer check
		self.dialyzer_path = self.settings.get('dialyzer_path', self.get_exe_path('dialyzer'))
		if test_path(self.dialyzer_path) == False:
			log("Erlang Dyalizer cannot be found.")
			return False

		# paths
		self.plugin_path = os.path.join(sublime.packages_path(), 'SublimErl')
		self.completions_path = os.path.join(self.plugin_path, "completion")
		self.support_path = os.path.join(self.plugin_path, "support")

		return True

	def strip_code_for_parsing(self, code):
		code = self.strip_comments(code)
		code = self.strip_quoted_content(code)
		return self.strip_record_with_dots(code)

	def strip_comments(self, code):
		# strip comments but keep the same character count
		return re.sub(re.compile(r"%(.*)\n"), lambda m: (len(m.group(0)) - 1) * ' ' + '\n', code)

	def strip_quoted_content(self, code):
		# strip quoted content
		regex = re.compile(r"(\"([^\"]*)\")", re.MULTILINE + re.DOTALL)
		for m in regex.finditer(code):
			code = code[:m.start()] + (len(m.groups()[0]) * ' ') + code[m.end():]
		return code

	def strip_record_with_dots(self, code):
		# strip records with dot notation
		return re.sub(re.compile(r"(\.[a-z]+)"), lambda m: len(m.group(0)) * ' ', code)

	def get_erlang_module_name(self, view):
		# find module declaration and get module name
		module_region = view.find(r"^\s*-\s*module\s*\(\s*(?:[a-zA-Z0-9_]+)\s*\)\s*\.", 0)
		if module_region != None:
			m = re.match(r"^\s*-\s*module\s*\(\s*([a-zA-Z0-9_]+)\s*\)\s*\.", view.substr(module_region))
			return m.group(1)

	def get_exe_path(self, name):
		retcode, data = self.execute_os_command('which %s' % name)
		data = data.strip()
		if retcode == 0 and len(data) > 0:
			return data

	def set_erlang_libs_path(self):
		# run escript to get erlang lib path
		os.chdir(self.support_path)
		escript_command = "sublimerl_utility.erl lib_dir"
		retcode, data = self.execute_os_command('%s %s' % (self.escript_path, escript_command))
		self.erlang_libs_path = data
		return self.erlang_libs_path != ''

	def set_completion_skip_erlang_libs(self):
		self.completion_skip_erlang_libs = self.settings.get('completion_skip_erlang_libs', [])

	def execute_os_command(self, os_cmd):
		# start proc
		p = subprocess.Popen(os_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=self.env)
		stdout, stderr = p.communicate()
		return (p.returncode, stdout)


	def shellquote(self, s):
		return "'" + s.replace("'", "'\\''") + "'"


# initialize
SUBLIMERL = SublimErlGlobal()


# project loader
class SublimErlProjectLoader():

	def __init__(self, view):
		# init
		self.view = view
		self.window = view.window()
		self.status_buffer = ''

		self.erlang_module_name = None
		self.project_root = None
		self.test_root = None
		self.app_name = None

		self.set_erlang_module_name()
		self.set_project_roots()
		self.set_app_name()

	def set_erlang_module_name(self):
		self.erlang_module_name = SUBLIMERL.get_erlang_module_name(self.view)

	def set_project_roots(self):
		# get project & file roots
		current_file_path = os.path.dirname(self.view.file_name())
		project_root, file_test_root = self.find_project_roots(current_file_path)

		if project_root == file_test_root == None:
			self.project_root = self.test_root = None
			return

		# save
		self.project_root = os.path.abspath(project_root)
		self.test_root = os.path.abspath(file_test_root)

	def find_project_roots(self, current_dir, project_root_candidate=None, file_test_root_candidate=None):
		# if rebar.config or an ebin directory exists, save as potential candidate
		if os.path.exists(os.path.join(current_dir, 'rebar.config')) or os.path.exists(os.path.join(current_dir, 'ebin')):
			# set project root candidate
			project_root_candidate = current_dir
			# set test root candidate if none set yet
			if file_test_root_candidate == None: file_test_root_candidate = current_dir

		current_dir_split = current_dir.split(os.sep)
		# if went up to root, stop and return current candidate
		if len(current_dir_split) < 2: return (project_root_candidate, file_test_root_candidate)
		# walk up directory
		current_dir_split.pop()
		return self.find_project_roots(os.sep.join(current_dir_split), project_root_candidate, file_test_root_candidate)

	def set_app_name(self):
		# get app file
		src_path = os.path.join(self.test_root, 'src')
		for f in os.listdir(src_path):
			if f.endswith('.app.src'):
				app_file_path = os.path.join(src_path, f)
				self.app_name = self.find_app_name(app_file_path)

	def find_app_name(self, app_file_path):
		f = open(app_file_path, 'rb')
		app_desc = f.read()
		f.close()
		m = re.search(r"{\s*application\s*,\s*('?[A-Za-z0-9_]+'?)\s*,\s*\[", app_desc)
		if m:
			return m.group(1)

	def update_status(self):
		if len(self.status_buffer):
			sublime.status_message(self.status_buffer)
			self.status_buffer = ''

	def status(self, text):
		self.status_buffer += text
		sublime.set_timeout(self.update_status, 0)

	def log(self, text):
		pass

	def get_test_env(self):
		env = SUBLIMERL.env.copy()
		env['PATH'] = "%s:%s:" % (env['PATH'], self.project_root)
		return env

	def compile_source(self, skip_deps=False):
		# compile to ebin
		options = 'skip_deps=true' if skip_deps else ''
		retcode, data = self.execute_os_command('%s compile %s' % (SUBLIMERL.rebar_path, options), dir_type='project', block=True, log=False)
		return (retcode, data)

	def shellquote(self, s):
		return SUBLIMERL.shellquote(s)

	def execute_os_command(self, os_cmd, dir_type=None, block=False, log=True):
		# set dir
		if dir_type == 'project': os.chdir(self.project_root)
		elif dir_type == 'test': os.chdir(self.test_root)

		if log == True: self.log("%s$ %s\n\n" % (os.getcwd(), os_cmd))

		# start proc
		current_env = self.get_test_env()
		p = subprocess.Popen(os_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=current_env)
		if block == True:
			stdout, stderr = p.communicate()
			return (p.returncode, stdout)
		else:
			stdout = []
			for line in p.stdout:
				self.log(line)
				stdout.append(line)
			return (p.returncode, ''.join(stdout))


# common text command class
class SublimErlTextCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		# run only if context matches
		if self._context_match():
			# check
			if SUBLIMERL.initialized == False:
				# self.log("SublimErl could not be initialized:\n\n%s\n" % '\n'.join(SUBLIMERL.init_errors))
				print "SublimErl could not be initialized:\n\n%s\n" % '\n'.join(SUBLIMERL.init_errors)
				return
			else:
				return self.run_command(edit)

	def _context_match(self):
		# context matches if lang is source.erlang and if platform is not windows
		caret = self.view.sel()[0].a
		if 'source.erlang' in self.view.scope_name(caret) and sublime.platform() != 'windows': return True
		else: return False

	def is_enabled(self):
		# context menu
		if self._context_match(): return self.show_contextual_menu()

	def show_contextual_menu(self):
		# can be overridden
		return True
