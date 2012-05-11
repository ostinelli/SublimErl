# ==========================================================================================================
# SublimErl - A Sublime Text 2 Plugin for Erlang Integrated Testing & Code Completion
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

import sublime, sublime_plugin
import sys, os, re, subprocess, threading, webbrowser

# globals
SUBLIMERL_VERSION = '0.2-RC2'

SUBLIMERL = {
	'last_test': None,
	'last_test_type': None,
	'project_root': None,
	'test_root': None
}


# core launcher & panel
class SublimErlLauncher():

	def __init__(self, view, new=True, show_log=True):
		# init
		self.panel_name = 'sublimerl'
		self.panel_buffer = ''
		self.status_buffer = ''
		self.view = view
		self.window = view.window()
		self.env = None
		self.show_log = show_log
		self.available = False
		# paths
		self.rebar_path = None
		self.erl_path = None
		self.escript_path = None
		self.dialyzer_path = None
		# test vars
		self.erlang_module_name = None
		self.new = new
		# setup panel
		self.setup_panel()
		# run setup
		self.setup_launcher()

	def setup_panel(self):
		if self.show_log == True:
			self.panel = self.window.get_output_panel(self.panel_name)
			# TODO: have this set as relative path
			self.panel.settings().set("syntax", os.path.join(self.plugin_path(), "theme", "SublimErl.hidden-tmLanguage"))
			self.panel.settings().set("color_scheme", os.path.join(self.plugin_path(), "theme", "SublimErl.hidden-tmTheme"))

	def update_panel(self):
		if len(self.panel_buffer):
			panel_edit = self.panel.begin_edit()
			self.panel.insert(panel_edit, self.panel.size(), self.panel_buffer)
			self.panel.end_edit(panel_edit)
			self.panel.show(self.panel.size())
			self.panel_buffer = ''
			# show/hide panel		
			if self.show_log:
				self.window.run_command("show_panel", {"panel": "output.%s" % self.panel_name})
			else:
				self.window.run_command("hide_panel", {"panel": "output.%s" % self.panel_name})

	def update_status(self):
		if len(self.status_buffer):
			sublime.status_message(self.status_buffer)
			self.status_buffer = ''

	def log(self, text):
		if self.show_log:
			self.panel_buffer += text
			sublime.set_timeout(self.update_panel, 0)

	def log_error(self, error_text):
		self.log("Error => %s\n[ABORTED]\n" % error_text)

	def status(self, text):
		self.status_buffer += text
		sublime.set_timeout(self.update_status, 0)

	def plugin_path(self):
		return os.path.join(sublime.packages_path(), 'SublimErl')

	def setup_launcher(self):
		# init test
		global SUBLIMERL_VERSION
		self.log("Starting tests (SublimErl v%s).\n" % SUBLIMERL_VERSION)

		if self.new == True:
			# file saved?
			if self.view.is_scratch():
				self.log_error("Please save this file to proceed.")
				return
			elif os.path.splitext(self.view.file_name())[1] != '.erl':
				self.log_error("This is not a .erl file.")
				return

			# get module and module_tests filename
			self.erlang_module_name = self.get_erlang_module_name()
			if self.erlang_module_name == None:
				self.log_error("Cannot find a -module declaration: please add one to proceed.")
				return

		# save project's root paths
		if self.save_project_roots() == False:
			self.log_error("This code does not seem to be part of an OTP compilant project.")
			return

		# set environment
		self.set_env()

		# paths check
		if self.get_paths() == None: return

		# ok we can use this launcher
		self.available = True

	def get_paths(self):
		settings = sublime.load_settings('SublimErl.sublime-settings')

		# rebar
		self.rebar_path = settings.get('rebar_path', self.get_exe_path('rebar'))
		if self.rebar_path == None or not os.path.exists(self.rebar_path):
			self.log_error("Rebar cannot be found, please download and install from <https://github.com/basho/rebar>.")
			return

		# erl check
		self.erl_path = settings.get('erl_path', self.get_exe_path('erl'))
		if self.erl_path == None or not os.path.exists(self.erl_path):
			self.log_error("Erlang binary (erl) cannot be found.")
			return

		# escript check
		self.escript_path = settings.get('escript_path', self.get_exe_path('escript'))
		if self.escript_path == None or not os.path.exists(self.escript_path):
			self.log_error("Erlang binary (escript) cannot be found.")
			return

		# dialyzer check
		self.dialyzer_path = settings.get('dialyzer_path', self.get_exe_path('dialyzer'))
		if self.dialyzer_path == None or not os.path.exists(self.dialyzer_path):
			self.log_error("Erlang Dyalizer cannot be found.")
			return

		return True

	def get_exe_path(self, name):
		retcode, data = self.execute_os_command('which %s' % name, block=True)
		data = data.strip()
		if retcode == 0 and len(data) > 0:
			return data

	def set_env(self):
		self.env = os.environ.copy()
		# add project root
		global SUBLIMERL
		self.env['PATH'] = "%s:%s" % (self.env['PATH'], SUBLIMERL['project_root'])
		# TODO: enhance the finding of paths
		if sublime.platform() == 'osx':
			# get relevant file paths
			etc_paths = ['/etc/paths']
			for f in os.listdir('/etc/paths.d'):
				etc_paths.append(os.path.abspath(f))
			# bash profile
			bash_profile_path = os.path.join(os.getenv('HOME'), '.bash_profile')
			# get env paths
			additional_paths = "%s:%s" % (self.readfiles_one_path_per_line(etc_paths), self.readfiles_exported_paths([bash_profile_path]))
			# add
			self.env['PATH'] = self.env['PATH'] + additional_paths

	def readfiles_one_path_per_line(self, file_paths):
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

	def readfiles_exported_paths(self, file_paths):
		concatenated_paths = []
		for file_path in file_paths:
			if os.path.exists(file_path):
				p = subprocess.Popen(". %s; env" % file_path, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
				data, stderr = p.communicate()
				env = dict((line.split("=", 1) for line in data.splitlines()))
				concatenated_paths.append(env['PATH'].strip())
		return ''.join(concatenated_paths)

	def get_erlang_module_name(self):
		# find module declaration and get module name
		module_region = self.view.find(r"^\s*-\s*module\s*\(\s*(?:[a-zA-Z0-9_]+)\s*\)\s*\.", 0)
		if module_region != None:
			m = re.match(r"^\s*-\s*module\s*\(\s*([a-zA-Z0-9_]+)\s*\)\s*\.", self.view.substr(module_region))
			return m.group(1)

	def save_project_roots(self):
		global SUBLIMERL

		# get project & file roots
		current_file_path = os.path.dirname(self.view.file_name())
		project_root, file_test_root = self.get_project_roots(current_file_path)

		if project_root == file_test_root == None:
			SUBLIMERL['project_root'] = SUBLIMERL['test_root'] = None
			return False

		# save
		SUBLIMERL['project_root'] = os.path.abspath(project_root)
		SUBLIMERL['test_root'] = os.path.abspath(file_test_root)

	def get_project_roots(self, current_dir, project_root_candidate=None, file_test_root_candidate=None):
		# if rebar.config or a src directory exists, save as potential candidate
		if os.path.exists(os.path.join(current_dir, 'rebar.config')) or os.path.exists(os.path.join(current_dir, 'src')):
			# set project root candidate
			project_root_candidate = current_dir
			# set test root candidate if none set yet
			if file_test_root_candidate == None: file_test_root_candidate = current_dir

		current_dir_split = current_dir.split(os.sep)
		# if went up to root, stop and return current candidate
		if len(current_dir_split) < 2: return (project_root_candidate, file_test_root_candidate)
		# walk up directory
		current_dir_split.pop()
		return self.get_project_roots(os.sep.join(current_dir_split), project_root_candidate, file_test_root_candidate)

	def get_project_root(self):
		global SUBLIMERL
		return SUBLIMERL['project_root']

	def execute_os_command(self, os_cmd, dir_type=None, block=False):
		# set dir
		global SUBLIMERL
		if dir_type == 'root': os.chdir(SUBLIMERL['project_root'])
		elif dir_type == 'test': os.chdir(SUBLIMERL['test_root'])
		# start proc
		p = subprocess.Popen(os_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=self.env)
		if block == True:
			stdout, stderr = p.communicate()
			return (p.returncode, stdout)
		else:
			stdout = []
			for line in p.stdout:
				self.log(line)
				stdout.append(line)
			return (p.returncode, ''.join(stdout))

	def shellquote(self, s):
		return "'" + s.replace("'", "'\\''") + "'"

	def compile_source(self):
		# compile to ebin
		retcode, data = self.execute_os_command('%s compile' % self.rebar_path, dir_type='root', block=True)

		
# test runner
class SublimErlTestRunner(SublimErlLauncher):

	def reset_current_test(self):
		global SUBLIMERL
		SUBLIMERL['last_test'] = None
		SUBLIMERL['last_test_type'] = None

	def start_test(self, dialyzer=False):
		# do not continue if no previous test exists and a redo was asked
		global SUBLIMERL
		if SUBLIMERL['last_test'] == None and self.new == False: return

		if self.new == True:
			# reset test
			self.reset_current_test()
			# save test type
			SUBLIMERL['last_test_type'] = self.get_test_type(dialyzer)

		if SUBLIMERL['last_test_type'] == 'eunit': self.start_eunit_test()
		elif SUBLIMERL['last_test_type'] == 'ct': self.start_ct_test()
		elif SUBLIMERL['last_test_type'] == 'dialyzer': self.start_dialyzer_test()

	def get_test_type(self, dialyzer):
		if dialyzer == True: return 'dialyzer'
		elif self.erlang_module_name.find("_SUITE") != -1: return 'ct'
		else: return 'eunit'

	def get_test_function_name(self):
		# get current line position
		cursor_position = self.view.sel()[0].a

		# find all regions with a test function definition
		function_regions = self.view.find_all(r"(%.*)?([a-zA-Z0-9_]*_test_\s*\(\s*\)\s*->[^.]*\.)")

		# loop regions
		matching_region = None
		for region in function_regions:
			region_content = self.view.substr(region)
			if not re.match(r"%.*((?:[a-zA-Z0-9_]*)_test_)\s*\(\s*\)\s*->", region_content):
				# function is not commented out, is cursor included in region?
				if region.a <= cursor_position and cursor_position <= region.b:
					matching_region = region
					break

		# get function name
		if matching_region != None:
			# get function name and arguments
			m = re.match(r"((?:[a-zA-Z0-9_]*)_test_)\s*\(\s*\)\s*->(?:.|\n)", self.view.substr(matching_region))
			if m != None:
				return "%s/0" % m.group(1)

	def start_eunit_test(self):
		global SUBLIMERL

		if self.new == True:
			# get test module name
			pos = self.erlang_module_name.find("_tests")
			if pos == -1:
				# tests are in the same file
				module_name = self.erlang_module_name
			else:
				# tests are in different files
				module_name = self.erlang_module_name[0:pos]

			# get function name depending on cursor position
			function_name = self.get_test_function_name()

			# save test
			module_tests_name = self.erlang_module_name
			SUBLIMERL['last_test'] = (module_name, module_tests_name, function_name)
		
		else:
			# retrieve test info
			module_name, module_tests_name, function_name = SUBLIMERL['last_test']

		# run test
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				this.eunit_test(module_name, module_tests_name, function_name)
		SublimErlThread().start()
		
	def start_ct_test(self):
		global SUBLIMERL

		if self.new == True:
			pos = self.erlang_module_name.find("_SUITE")
			module_tests_name = self.erlang_module_name[0:pos]

			# save test
			SUBLIMERL['last_test'] = module_tests_name
		
		else:
			module_tests_name = SUBLIMERL['last_test']

		# run test
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				this.ct_test(module_tests_name)
		SublimErlThread().start()

	def start_dialyzer_test(self):
		global SUBLIMERL

		if self.new == True:
			# save test
			module_tests_name = self.erlang_module_name
			SUBLIMERL['last_test'] = module_tests_name
		
		else:
			module_tests_name = SUBLIMERL['last_test']

		# run test
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				this.dialyzer_test(module_tests_name)
		SublimErlThread().start()

	def eunit_test(self, module_name, module_tests_name, function_name):
		if function_name != None:
			# specific function provided, start single test
			self.log("Running test \"%s:%s\" for target module \"%s.erl\".\n\n" % (module_tests_name, function_name, module_name))
			# compile all source code and test module
			if self.compile_eunit_no_run() != 0: return
			# run single test
			self.run_single_eunit_test(module_tests_name, function_name)
		else:
			# run all test functions in file
			if module_tests_name != module_name:
				self.log("Running all tests in module \"%s.erl\" for target module \"%s.erl\".\n\n" % (module_tests_name, module_name))
			else:
				self.log("Running all tests for target module \"%s.erl\".\n\n" % module_name)
			# compile all source code and test module
			self.compile_eunit_run_suite(module_tests_name)

	def compile_eunit_no_run(self):
		# call rebar to compile -  HACK: passing in a non-existing suite forces rebar to not run the test suite
		retcode, data = self.execute_os_command('%s eunit suite=sublimerl_unexisting_test' % self.rebar_path, dir_type='test', block=True)
		if re.search(r"sublimerl_unexisting_test", data) != None:
			# expected error returned (due to the hack)
			return 0
		# interpret
		self.interpret_eunit_test_results(retcode, data)

	def run_single_eunit_test(self, module_tests_name, function_name):
		# build & run erl command
		mod_function = "%s:%s" % (module_tests_name, function_name)
		erl_command = "-noshell -pa .eunit -eval \"eunit:test({generator, fun %s})\" -s init stop" % mod_function

		retcode, data = self.execute_os_command('%s %s' % (self.erl_path, erl_command), dir_type='test', block=False)
		# interpret
		self.interpret_eunit_test_results(retcode, data)

	def compile_eunit_run_suite(self, suite):
		retcode, data = self.execute_os_command('%s eunit suite=%s' % (self.rebar_path, suite), dir_type='test', block=False)
		# interpret
		self.interpret_eunit_test_results(retcode, data)

	def interpret_eunit_test_results(self, retcode, data):
		# get outputs
		if re.search(r"Test passed.", data):
			# single test passed
			self.log("\n=> TEST PASSED.\n")

		elif re.search(r"All \d+ tests passed.", data):
			# multiple tests passed
			passed_count = re.search(r"All (\d+) tests passed.", data).group(1)
			self.log("\n=> %s TESTS PASSED.\n" % passed_count)

		elif re.search(r"Failed: \d+.", data):
			# some tests failed
			failed_count = re.search(r"Failed: (\d+).", data).group(1)
			self.log("\n=> %s TEST(S) FAILED.\n" % failed_count)

		elif re.search(r"There were no tests to run.", data):
			self.log("\n=> NO TESTS TO RUN.\n")

		else:
			self.log("\n=> TEST(S) FAILED.\n")

	def ct_test(self, module_tests_name):
		# run CT for suite
		self.log("Running tests of Common Tests SUITE \"%s_SUITE.erl\".\n\n" % module_tests_name)
		# compile all source code
		self.compile_source()
		# run suite
		retcode, data = self.execute_os_command('%s ct suites=%s' % (self.rebar_path, module_tests_name), dir_type='test', block=False)
		# interpret
		self.interpret_ct_test_results(retcode, data)

	def interpret_ct_test_results(self, retcode, data):
		# get outputs
		if re.search(r"DONE.", data):
			# test passed
			passed_count = re.search(r"(\d+) ok, 0 failed of \d+ test cases", data).group(1)
			if int(passed_count) > 0:
				self.log("=> %s TEST(S) PASSED.\n" % passed_count)
			else:
				self.log("=> NO TESTS TO RUN.\n")

		elif re.search(r"ERROR: One or more tests failed", data):
			failed_count = re.search(r"\d+ ok, (\d+) failed of \d+ test cases", data).group(1)
			self.log("\n=> %s TEST(S) FAILED.\n" % failed_count)
			self.log("** Hint: hit Ctrl-Alt-F8 (by default) to show a browser with Common Tests' results. **\n")

		else:
			self.log("\n=> TEST(S) FAILED.\n")

	def dialyzer_test(self, module_tests_name):
		# run dialyzer for file
		self.log("Running Dialyzer tests for \"%s.erl\".\n\n" % module_tests_name)
		# compile eunit
		self.compile_eunit_no_run()
		# run dialyzer
		retcode, data = self.execute_os_command('%s -n .eunit/%s.beam' % (self.dialyzer_path, module_tests_name), dir_type='test', block=False)
		# interpret
		self.interpret_dialyzer_test_results(retcode, data)

	def interpret_dialyzer_test_results(self, retcode, data):
		# get outputs
		if re.search(r"passed successfully", data):
			self.log("\n=> TEST(S) PASSED.\n")
		else:
			self.log("\n=> TEST(S) FAILED.\n")



# common text command class
class SublimErlTextCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		# run only if context matches
		if self._context_match(): return self.run_command(edit)

	def _context_match(self):
		# context matches if lang is source.erlang and if platfomr is not windows
		caret = self.view.sel()[0].a
		if 'source.erlang' in self.view.scope_name(caret) and sublime.platform() != 'windows': return True
		else: return False

	def is_enabled(self):
		# context menu
		if self._context_match(): return self.show_contextual_menu()

	def show_contextual_menu(self):
		# can be overridden
		return True

# start new test
class SublimErlTestCommand(SublimErlTextCommand):
	def run_command(self, edit):
		# init
		test_runner = SublimErlTestRunner(self.view)
		if test_runner.available == False: return
		# run tests
		test_runner.start_test()

# start new test
class SublimErlDialyzerCommand(SublimErlTextCommand):
	def run_command(self, edit):
		# init
		test_runner = SublimErlTestRunner(self.view)
		if test_runner.available == False: return
		# run tests
		test_runner.start_test(dialyzer=True)

# repeat last test
class SublimErlTestRedoCommand(SublimErlTextCommand):
	def run_command(self, edit):
		# init
		test_runner = SublimErlTestRunner(self.view, new=False)
		if test_runner.available == False: return
		# run tests
		test_runner.start_test()

	def show_contextual_menu(self):
		global SUBLIMERL
		return SUBLIMERL['last_test'] != None

# open CT results
class SublimErlCtResultsCommand(SublimErlTextCommand):
	def run_command(self, edit):
		# init
		launcher = SublimErlLauncher(self.view, show_log=False, new=False)
		if launcher.available == False: return
		# open CT results
		index_path = os.path.abspath(os.path.join('logs', 'index.html'))
		if os.path.exists(index_path): webbrowser.open(index_path)

	def show_contextual_menu(self):
		global SUBLIMERL
		index_path = os.path.abspath(os.path.join(SUBLIMERL['test_root'], 'logs', 'index.html'))
		return os.path.exists(index_path)

