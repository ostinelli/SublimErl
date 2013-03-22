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


# imports
import sublime
import os, subprocess, re, threading, webbrowser
from sublimerl_core import SUBLIMERL_VERSION, SUBLIMERL, SublimErlTextCommand, SublimErlProjectLoader


# test runner
class SublimErlTestRunner(SublimErlProjectLoader):

	def __init__(self, view):
		# init super
		SublimErlProjectLoader.__init__(self, view)

		# init
		self.initialized = False
		self.panel_name = 'sublimerl_tests'
		self.panel_buffer = ''

		# don't proceed if a test is already running
		global SUBLIMERL
		if SUBLIMERL.test_in_progress == True: return
		SUBLIMERL.test_in_progress = True

		# setup panel
		self.setup_panel()
		# run
		if self.init_tests() == True:
			self.initialized = True
		else:
			SUBLIMERL.test_in_progress = False

	def setup_panel(self):
		self.panel = self.window.get_output_panel(self.panel_name)
		self.panel.settings().set("syntax", os.path.join(SUBLIMERL.plugin_path, "theme", "SublimErlTests.hidden-tmLanguage"))
		self.panel.settings().set("color_scheme", os.path.join(SUBLIMERL.plugin_path, "theme", "SublimErlTests.hidden-tmTheme"))

	def update_panel(self):
		if len(self.panel_buffer):
			panel_edit = self.panel.begin_edit()
			self.panel.insert(panel_edit, self.panel.size(), self.panel_buffer)
			self.panel.end_edit(panel_edit)
			self.panel.show(self.panel.size())
			self.panel_buffer = ''
			self.window.run_command("show_panel", {"panel": "output.%s" % self.panel_name})

	def log(self, text):
		self.panel_buffer += text.encode('utf-8')
		sublime.set_timeout(self.update_panel, 0)

	def log_error(self, error_text):
		self.log("Error => %s\n[ABORTED]\n" % error_text)

	def init_tests(self):
		if SUBLIMERL.initialized == False:
			self.log("SublimErl could not be initialized:\n\n%s\n" % '\n'.join(SUBLIMERL.init_errors))

		# file saved?
		if self.view.is_scratch():
			self.log_error("Please save this file to proceed.")
			return False
		elif os.path.splitext(self.view.file_name())[1] != '.erl':
			self.log_error("This is not a .erl file.")
			return False

		# check module name
		if self.erlang_module_name == None:
			self.log_error("Cannot find a -module declaration: please add one to proceed.")
			return False

		# save project's root paths
		if self.project_root == None or self.test_root == None:
			self.log_error("This code does not seem to be part of an OTP compilant project.")
			return False

		# all ok
		return True

	def compile_eunit_no_run(self):
		# call rebar to compile -  HACK: passing in a non-existing suite forces rebar to not run the test suite
		os_cmd = '%s eunit suites=sublimerl_unexisting_test' % SUBLIMERL.rebar_path
		if self.app_name: os_cmd += ' apps=%s' % self.app_name
		retcode, data = self.execute_os_command(os_cmd, dir_type='project', block=True, log=False)

		if re.search(r"There were no tests to run", data) != None:
			# expected error returned (due to the hack)
			return 0
		# send the data to panel
		self.log(data)

	def reset_last_test(self):
		global SUBLIMERL

		SUBLIMERL.last_test = None
		SUBLIMERL.last_test_type = None

	def start_test(self, new=True):
		# do not continue if no previous test exists and a redo was asked
		if SUBLIMERL.last_test == None and new == False: return
		# set test
		if new == True: self.reset_last_test()
		# test callback
		self.log("Starting tests (SublimErl v%s).\n" % SUBLIMERL_VERSION)
		self.start_test_cmd(new)

	def start_test_cmd(self, new):
		# placeholder for inheritance
		pass

	def on_test_ended(self):
		global SUBLIMERL
		SUBLIMERL.test_in_progress = False


# dialyzer test runner
class SublimErlDialyzerTestRunner(SublimErlTestRunner):

	def start_test_cmd(self, new):
		global SUBLIMERL

		if new == True:
			# save test module
			module_tests_name = self.erlang_module_name

			SUBLIMERL.last_test = module_tests_name
			SUBLIMERL.last_test_type = 'dialyzer'
		else:
			# retrieve test module
			module_tests_name = SUBLIMERL.last_test

		# run test
		this = self
		filename = self.view.file_name()
		class SublimErlThread(threading.Thread):
			def run(self):
				this.dialyzer_test(module_tests_name, filename)
		SublimErlThread().start()

	def dialyzer_test(self, module_tests_name, filename):
		# run dialyzer for file
		self.log("Running Dialyzer tests for \"%s\".\n\n" % filename)
		# compile eunit
		self.compile_eunit_no_run()
		# run dialyzer
		retcode, data = self.execute_os_command('%s -n .eunit/%s.beam' % (SUBLIMERL.dialyzer_path, module_tests_name), dir_type='test', block=False)
		# interpret
		self.interpret_test_results(retcode, data)

	def interpret_test_results(self, retcode, data):
		# get outputs
		if re.search(r"passed successfully", data):
			self.log("\n=> TEST(S) PASSED.\n")
		else:
			self.log("\n=> TEST(S) FAILED.\n")

		# free test
		self.on_test_ended()


# eunit test runner
class SublimErlEunitTestRunner(SublimErlTestRunner):

	def start_test_cmd(self, new):
		global SUBLIMERL

		# run test
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
			SUBLIMERL.last_test = (module_name, module_tests_name, function_name)
			SUBLIMERL.last_test_type = 'eunit'

		else:
			# retrieve test info
			module_name, module_tests_name, function_name = SUBLIMERL.last_test

		# run test
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				this.eunit_test(module_name, module_tests_name, function_name)
		SublimErlThread().start()

	def get_test_function_name(self):
		# get current line position
		cursor_position = self.view.sel()[0].a
		# get module content
		region_full = sublime.Region(0, self.view.size())
		module = SUBLIMERL.strip_code_for_parsing(self.view.substr(region_full))
		# parse regions
		regex = re.compile(r"([a-z0-9][a-zA-Z0-9_]*_test(_)?\s*\(\s*\)\s*->[^.]*\.)", re.MULTILINE)
		for m in regex.finditer(module):
			if m.start() <= cursor_position and cursor_position <= m.end():
				function_content = m.groups()[0]
				return function_content[:function_content.index('(')]

	def eunit_test(self, module_name, module_tests_name, function_name):
		if function_name != None:
			# specific function provided, start single test
			self.log("Running test \"%s:%s/0\" for target module \"%s.erl\".\n\n" % (module_tests_name, function_name, module_name))
			# compile source code and run single test
			self.compile_eunit_run_suite(module_tests_name, function_name)
		else:
			# run all test functions in file
			if module_tests_name != module_name:
				self.log("Running all tests in module \"%s.erl\" for target module \"%s.erl\".\n\n" % (module_tests_name, module_name))
			else:
				self.log("Running all tests for target module \"%s.erl\".\n\n" % module_name)
			# compile all source code and test module
			self.compile_eunit_run_suite(module_tests_name)

	def compile_eunit_run_suite(self, suite, function_name=None):
		os_cmd = '%s eunit suites=%s' % (SUBLIMERL.rebar_path, suite)

		if function_name != None: os_cmd += ' tests=%s' % function_name
		if self.app_name: os_cmd += ' apps=%s' % self.app_name

		os_cmd += ' skip_deps=true'

		retcode, data = self.execute_os_command(os_cmd, dir_type='project', block=False)
		# interpret
		self.interpret_test_results(retcode, data)

	def interpret_test_results(self, retcode, data):
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
			self.log(data)
			self.log("\n=> TEST(S) FAILED.\n")

		# free test
		self.on_test_ended()


# eunit test runner
class SublimErlCtTestRunner(SublimErlTestRunner):

	def start_test_cmd(self, new):
		global SUBLIMERL

		# run test
		if new == True:
			pos = self.erlang_module_name.find("_SUITE")
			module_tests_name = self.erlang_module_name[0:pos]

			# save test
			SUBLIMERL.last_test = module_tests_name
			SUBLIMERL.last_test_type = 'ct'

		else:
			module_tests_name = SUBLIMERL.last_test

		# run test
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				this.ct_test(module_tests_name)
		SublimErlThread().start()

	def ct_test(self, module_tests_name):
		# run CT for suite
		self.log("Running tests of Common Tests SUITE \"%s_SUITE.erl\".\n\n" % module_tests_name)
		os_cmd = '%s ct suites=%s skip_deps=true' % (SUBLIMERL.rebar_path, module_tests_name)
		# compile all source code
		self.compile_source()
		# run suite
		retcode, data = self.execute_os_command(os_cmd, dir_type='test', block=False)
		# interpret
		self.interpret_test_results(retcode, data)

	def interpret_test_results(self, retcode, data):
		# get outputs
		if re.search(r"DONE.", data):
			# test passed
			passed_count = re.search(r"(\d+) ok, 0 failed(?:, 1 skipped)? of \d+ test cases", data).group(1)
			if int(passed_count) > 0:
				self.log("=> %s TEST(S) PASSED.\n" % passed_count)
			else:
				self.log("=> NO TESTS TO RUN.\n")

		elif re.search(r"ERROR: One or more tests failed", data):
			failed_count = re.search(r"\d+ ok, (\d+) failed(?:, 1 skipped)? of \d+ test cases", data).group(1)
			self.log("\n=> %s TEST(S) FAILED.\n" % failed_count)

		else:
			self.log("\n=> TEST(S) FAILED.\n")

		# free test
		self.on_test_ended()


### Commands
# test runners
class SublimErlTestRunners():

	def dialyzer_test(self, view):
		test_runner = SublimErlDialyzerTestRunner(view)
		if test_runner.initialized == False: return
		test_runner.start_test()

	def ct_or_eunit_test(self, view, new=True):
		if SUBLIMERL.last_test_type == 'ct' or SUBLIMERL.get_erlang_module_name(view).find("_SUITE") != -1:
			# ct
			test_runner = SublimErlCtTestRunner(view)
		else:
			# eunit
			test_runner = SublimErlEunitTestRunner(view)

		if test_runner.initialized == False: return
		test_runner.start_test(new=new)


# dialyzer tests
class SublimErlDialyzerCommand(SublimErlTextCommand):
	def run_command(self, edit):
		SublimErlTestRunners().dialyzer_test(self.view)


# start new test
class SublimErlTestCommand(SublimErlTextCommand):
	def run_command(self, edit):
		SublimErlTestRunners().ct_or_eunit_test(self.view)


# repeat last test
class SublimErlRedoCommand(SublimErlTextCommand):
	def run_command(self, edit):
		# init
		if SUBLIMERL.last_test_type == 'dialyzer': SublimErlTestRunners().dialyzer_test(self.view, new=False)
		elif SUBLIMERL.last_test_type == 'eunit' or SUBLIMERL.last_test_type == 'ct': SublimErlTestRunners().ct_or_eunit_test(self.view, new=False)

	def show_contextual_menu(self):
		return SUBLIMERL.last_test != None


# open CT results
class SublimErlCtResultsCommand(SublimErlTextCommand):
	def run_command(self, edit):
		# open CT results
		loader = SublimErlProjectLoader(self.view)
		index_path = os.path.abspath(os.path.join(loader.project_root, 'logs', 'index.html'))
		if os.path.exists(index_path): webbrowser.open(index_path)

	def show_contextual_menu(self):
		loader = SublimErlProjectLoader(self.view)
		index_path = os.path.abspath(os.path.join(loader.project_root, 'logs', 'index.html'))
		return os.path.exists(index_path)
