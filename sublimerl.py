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


# globals
SUBLIMERL_VERSION = '0.1'
SUBLIMERL_CURRENT_TEST = None
SUBLIMERL_CURRENT_TEST_TYPE = None


# core launcher & panel
class SublimErlLauncher():

	def __init__(self, view, show_log=True):
		# init
		self.panel_name = 'sublimerl'
		self.panel_buffer = ''
		self.view = view
		self.window = view.window()
		self.rebar_path = None
		self.erl_path = None
		self.env = None
		self.show_log = show_log
		self.available = False
		# test vars
		self.erlang_module_name = None
		# setup panel
		self.panel = self.window.get_output_panel(self.panel_name)
		self.panel.settings().set("syntax", "Packages/SublimErl/SublimErl.tmLanguage")
		self.panel.settings().set("color_scheme", "Packages/SublimErl/SublimErl.tmTheme")
		# run setup
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
		if self.show_log:
			self.panel_buffer += text
			sublime.set_timeout(self.update_panel, 0)

	def log_error(self, error_text):
		self.log("Error => %s\n[ABORTED]\n" % error_text)

	def setup(self):
		# init test
		global SUBLIMERL_VERSION
		self.log("Starting tests (SublimErl v%s).\n" % SUBLIMERL_VERSION)

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
				stdout.append(line)
			return (p.returncode, ''.join(stdout))

	def compile_all(self):
		# compile to ebin
		retcode, data = self.execute_os_command('%s compile' % self.rebar_path, True)


# test runner
class SublimErlTestRunner(SublimErlLauncher):

	def start_test(self, new=True):
		# do not continue if no previous test exists and a redo was asked
		global SUBLIMERL_CURRENT_TEST, SUBLIMERL_CURRENT_TEST_TYPE
		if SUBLIMERL_CURRENT_TEST == None and new == False: return

		if new == True:
			# reset test
			SUBLIMERL_CURRENT_TEST = None
			# save test type
			SUBLIMERL_CURRENT_TEST_TYPE = self.get_test_type()
		
		if SUBLIMERL_CURRENT_TEST_TYPE == 'eunit': self.start_eunit_test(new)
		elif SUBLIMERL_CURRENT_TEST_TYPE == 'ct': self.start_ct_test(new)

	def get_test_type(self):
		if self.erlang_module_name.find("_SUITE") != -1: return 'ct'
		return 'eunit'

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

	def start_eunit_test(self, new=True):
		global SUBLIMERL_CURRENT_TEST

		if new == True:
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
			SUBLIMERL_CURRENT_TEST = (module_name, module_tests_name, function_name)
		
		else:
			# retrieve test info
			module_name, module_tests_name, function_name = SUBLIMERL_CURRENT_TEST

		# run test
		self.eunit_test(module_name, module_tests_name, function_name)

	def start_ct_test(self, new=True):
		global SUBLIMERL_CURRENT_TEST

		if new == True:
			pos = self.erlang_module_name.find("_SUITE")
			module_tests_name = self.erlang_module_name[0:pos]

			# save test
			SUBLIMERL_CURRENT_TEST = module_tests_name
		
		else:
			module_tests_name = SUBLIMERL_CURRENT_TEST

		# run test
		self.ct_test(module_tests_name)

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
			self.log("Running all tests in module \"%s.erl\" for target module \"%s.erl\".\n\n" % (module_tests_name, module_name))
			# compile all source code and test module
			self.compile_eunit_run_suite(module_tests_name)

	def compile_eunit_no_run(self):
		# call rebar to compile -  HACK: passing in a non-existing suite forces rebar to not run the test suite
		retcode, data = self.execute_os_command('%s eunit suite=sublimerl_unexisting_test' % self.rebar_path, True)
		if re.search(r"sublimerl_unexisting_test", data) != None:
			# expected error returned (due to the hack)
			return 0
		# interpret
		self.interpret_eunit_test_results(retcode, data)

	def compile_eunit_run_suite(self, suite):
		retcode, data = self.execute_os_command('%s eunit suite=%s' % (self.rebar_path, suite), False)
		# interpret
		self.interpret_eunit_test_results(retcode, data)

	def run_single_eunit_test(self, module_tests_name, function_name):
		# build & run erl command
		mod_function = "%s:%s" % (module_tests_name, function_name)
		erl_command = "-noshell -pa .eunit -eval \"eunit:test({generator, fun %s})\" -s init stop" % mod_function
		retcode, data = self.execute_os_command('%s %s' % (self.erl_path, erl_command), False)
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

		else:
			self.log("\n=> TEST(S) FAILED.\n")

	def ct_test(self, module_tests_name):
		# run CT for suite
		self.log("Running tests of Common Tests SUITE \"%s.erl\".\n\n" % module_tests_name)
		# compile all source code and test module
		self.compile_all()
		self.run_ct_suite(module_tests_name)
			
	def run_ct_suite(self, module_tests_name):
		retcode, data = self.execute_os_command('%s ct suites=%s' % (self.rebar_path, module_tests_name), False)
		# interpret
		self.interpret_ct_test_results(retcode, data)

	def interpret_ct_test_results(self, retcode, data):
		# get outputs
		if re.search(r"DONE.", data):
			# test passed
			passed_count = re.search(r"(\d+) ok, 0 failed of \d+ test cases", data).group(1)
			self.log("=> %s TEST(S) PASSED.\n" % passed_count)
			return

		elif re.search(r"ERROR: One or more tests failed", data):
			failed_count = re.search(r"\d+ ok, (\d+) failed of \d+ test cases", data).group(1)
			self.log("\n=> %s TEST(S) FAILED.\n" % failed_count)
			self.log("** Hint: hit Command+Shift+C (by default) to show a browser with results. **\n")

		else:
			self.log("\n=> TEST(S) FAILED.\n")

# start new test
class SublimErlTestCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		# init
		test_runner = SublimErlTestRunner(self.view)
		if test_runner.available == False: return
		# run tests
		test_runner.start_test()

# repeat last test
class SublimErlTestRedoCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		# init
		test_runner = SublimErlTestRunner(self.view)
		if test_runner.available == False: return
		# run tests
		test_runner.start_test(new=True)

