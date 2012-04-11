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

SUBLIMERL_CURRENT_TEST = None
SUBLIMERL_CURRENT_TEST_TYPE = None


# start new test
class SublimErlCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		SublimErlCore(self.view).start_test()

# redo previous test
class SublimErlRedoCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		global SUBLIMERL_CURRENT_TEST
		if SUBLIMERL_CURRENT_TEST == None: return
		SublimErlCore(self.view).start_test(new=False)

# open CT results
class SublimErlShowCtCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		core = SublimErlCore(self.view, panel=False)
		core.set_cwd_to_otp_project_root()
		index_path = os.path.abspath(os.path.join('logs', 'index.html'))
		if os.path.exists(index_path): webbrowser.open(index_path)

# listener on save
class SublimErlListener(sublime_plugin.EventListener):
	def on_post_save(self, view):
		# a view has been saved
		core = SublimErlCore(view, panel=False)
		core.set_cwd_to_otp_project_root()
		# run compile on separate thread to avoid blocking the editor
		class SublimErlSaveThread(threading.Thread):
			def run(self):
				core.test_runner.compile_all()
		SublimErlSaveThread().start()


# test prepare core
class SublimErlCore():

	def __init__(self, view, panel=True):
		self.view = view
		self.test_runner = SublimErlTestRunner(self)
		if panel == True: self.panel = SublimErlPanel(self.view)

		
	def set_cwd_to_otp_project_root(self):
		# get project root
		project_test_dir = os.path.dirname(self.view.file_name())
		project_root_path_arr = project_test_dir.split(os.sep)
		project_root_path_arr.pop()
		project_root_dir = os.sep.join(project_root_path_arr)

		# set current directory to root - needed by rebar
		os.chdir(os.path.abspath(project_root_dir))


	def start_test(self, new=True):
		# is this a .erl file?
		if not self.view.is_scratch():
			if os.path.splitext(self.view.file_name())[1] != '.erl':
				return

		# do not continue if no previous test exists and a redo was asked
		global SUBLIMERL_CURRENT_TEST, SUBLIMERL_CURRENT_TEST_TYPE
		if SUBLIMERL_CURRENT_TEST == None and new == False: return

		# get module and module_tests filename
		module_tests_name = self.get_module_name()
		if module_tests_name == None: return

		# init test
		self.log("Starting tests (SublimErl v%s).\n" % SUBLIMERL_VERSION)

		# file is saved?
		if self.view.is_scratch():
			self.log_error("This file has not been saved on disk: cannot start tests.")
			return

		# set cwd to project's root path - so that rebar can access it
		self.set_cwd_to_otp_project_root()

		# rebar check
		if self.rebar_exists() == False:
			self.log_error("Rebar cannot be found, please download and install from <https://github.com/basho/rebar>.")
			return

		# erl check
		if self.erl_exists() == False:
			self.log_error("Erlang binary (erl) cannot be found.")
			return

		if new == True:
			# reset test
			SUBLIMERL_CURRENT_TEST = None
			# get type
			SUBLIMERL_CURRENT_TEST_TYPE = self.get_test_type(module_tests_name)
		
		if SUBLIMERL_CURRENT_TEST_TYPE == 'eunit':
			self.start_eunit_test(module_tests_name, new)
		elif SUBLIMERL_CURRENT_TEST_TYPE == 'ct':
			self.start_ct_test(module_tests_name, new)
		else:
			self.log_error("Could not find tests to run.")


	def get_test_type(self, module_tests_name):
		if module_tests_name.find("_SUITE") != -1:
			return 'ct'
		return 'eunit'


	def start_eunit_test(self, module_tests_name, new=True):
		global SUBLIMERL_CURRENT_TEST

		if new == True:
			# get test
			pos = module_tests_name.find("_tests")
			if pos == -1:
				# tests are in the same file
				module_name = module_tests_name
			else:
				# tests are in different files
				module_name = module_tests_name[0:pos]
			module_filename = "%s.erl" % module_name

			# get function name depending on cursor position
			function_name = self.get_test_function_name()

			# save test
			SUBLIMERL_CURRENT_TEST = (module_filename, module_tests_name, function_name)
		
		else:
			module_filename, module_tests_name, function_name = SUBLIMERL_CURRENT_TEST

		# run test
		self.test_runner.eunit_test(module_filename, module_tests_name, function_name)


	def start_ct_test(self, module_tests_name, new=True):
		global SUBLIMERL_CURRENT_TEST

		if new == True:
			pos = module_tests_name.find("_SUITE")
			module_tests_name = module_tests_name[0:pos]

			# save test
			SUBLIMERL_CURRENT_TEST = module_tests_name
		
		else:
			module_tests_name = SUBLIMERL_CURRENT_TEST

		# run test
		self.test_runner.ct_test(module_tests_name)


	def get_module_name(self):
		# find module declaration and get module name
		module_region = self.view.find(r"^\s*-module\((?:[a-zA-Z0-9_]+)\)\.", 0)
		if module_region != None:
			m = re.match(r"^\s*-module\(([a-zA-Z0-9_]+)\)\.", self.view.substr(module_region))
			return m.group(1)


	def get_test_function_name(self):
		# get current line position
		cursor_position = self.view.sel()[0].a

		# find all regions with a test function definition
		function_regions = self.view.find_all(r"(%.*)?([a-zA-Z0-9_]*_test_\(\)\s*->[^.]*\.)")

		# loop regions
		matching_region = None
		for region in function_regions:
			region_content = self.view.substr(region)
			if not re.match(r"%.*((?:[a-zA-Z0-9_]*)_test_)\(\)\s*->", region_content):
				# function is not commented out, is cursor included in region?
				if region.a <= cursor_position and cursor_position <= region.b:
					matching_region = region
					break

		# get function name
		if matching_region != None:
			# get function name and arguments
			m = re.match(r"((?:[a-zA-Z0-9_]*)_test_)\(\)\s*->(?:.|\n)", self.view.substr(matching_region))
			if m != None:
				return "%s/0" % m.group(1)


	def rebar_exists(self):
		return self.test_runner.rebar_exists()

	def erl_exists(self):
		return self.test_runner.erl_exists()

	def log(self, text):
		self.panel.write_to_panel(text)

	def log_error(self, text):
		self.log("Error => %s\n[ABORTED]\n" % text)


# panel
class SublimErlPanel():

	def __init__(self, view):
		# init
		self.window = view.window()
		# create panel
		self.panel_name = 'sublimerl_panel'
		self.output_panel = self.window.get_output_panel(self.panel_name)
		# color scheme
		self.output_panel.settings().set("syntax", "Packages/SublimErl/SublimErl.tmLanguage")
		self.output_panel.settings().set("color_scheme", "Packages/SublimErl/SublimErl.tmTheme")


	def write_to_panel(self, text):
		# output to the panel
		panel = self.output_panel
		panel_edit = panel.begin_edit()
		panel.insert(panel_edit, panel.size(), text)
		panel.end_edit(panel_edit)
		panel.show(panel.size())
		# shot panel
		self.window.run_command("show_panel", {"panel": "output." + self.panel_name})


# test runner
class SublimErlTestRunner():

	def __init__(self, parent):
		# imported from parent
		self.log = parent.log
		self.log_error = parent.log_error
		# get paths
		self.rebar_path = self.get_rebar_path()
		self.erl_path = self.get_erl_path()


	def set_env(self):
		# TODO: find real path variable
		# TODO: save in init var
		env = os.environ
		env['PATH'] = os.environ['PATH'] + ':/usr/local/bin'
		return env


	def execute_os_command(self, os_cmd):
		p = subprocess.Popen(os_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True, env=self.set_env())
		stdout, stderr = p.communicate()
		return (p.returncode, stdout, stderr)


	def rebar_exists(self):
		return self.rebar_path != None


	def erl_exists(self):
		return self.erl_path != None


	def get_rebar_path(self):
		retcode, data, sterr = self.execute_os_command('which rebar')
		data = data.strip()
		if retcode == 0 and len(data) > 0:
			return data


	def get_erl_path(self):
		retcode, data, sterr = self.execute_os_command('which erl')
		data = data.strip()
		if retcode == 0 and len(data) > 0:
			return data


	def eunit_test(self, module_filename, module_tests_name, function_name):
		if function_name != None:
			# specific function provided, start single test
			self.log("Running test \"%s:%s\" for target module \"%s\".\n" % (module_tests_name, function_name, module_filename))
			# compile all source code and test module
			if self.compile_eunit_no_run() != 0: return		
			# run single test
			self.run_single_test(module_tests_name, function_name)
		else:
			# run all test functions in file
			self.log("Running all tests in module \"%s.erl\" for target module \"%s\".\n" % (module_tests_name, module_filename))
			# compile all source code and test module
			self.compile_eunit_run_suite(module_tests_name)


	def ct_test(self, module_tests_name):
		# run CT for suite
		self.log("Running tests of Common Tests SUITE \"%s.erl\".\n" % module_tests_name)
		# compile all source code and test module
		self.compile_all()
		self.run_ct_suite(module_tests_name)


	def compile_all(self):
		# compile to ebin
		retcode, data, sterr = self.execute_os_command('%s compile' % self.rebar_path)


	def compile_eunit_no_run(self):
		# call rebar to compile -  HACK: passing in a non-existing suite forces rebar to not run the test suite
		retcode, data, sterr = self.execute_os_command('%s eunit suite=sublimerl_unexisting_test' % self.rebar_path)
		if re.search(r"sublimerl_unexisting_test", data) != None:
			# expected error returned (due to the hack)
			return 0
		# interpret
		self.interpret_eunit_test_results(retcode, data, sterr)

	
	def compile_eunit_run_suite(self, suite):
		retcode, data, sterr = self.execute_os_command('%s eunit suite=%s' % (self.rebar_path, suite))
		# interpret
		self.interpret_eunit_test_results(retcode, data, sterr)


	def run_single_test(self, module_tests_name, function_name):
		# build & run erl command
		mod_function = "%s:%s" % (module_tests_name, function_name)
		erl_command = "-noshell -pa .eunit -eval \"eunit:test({generator, fun %s})\" -s init stop" % mod_function
		retcode, data, sterr = self.execute_os_command('%s %s' % (self.erl_path, erl_command))
		# interpret
		self.interpret_eunit_test_results(retcode, data, sterr)


	def interpret_eunit_test_results(self, retcode, data, sterr):
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
			self.log('\n' + data)
			failed_count = re.search(r"Failed: (\d+).", data).group(1)
			self.log("\n=> %s TEST(S) FAILED.\n" % failed_count)

		else:
			self.log('\n' + data)
			self.log("\n=> TEST(S) FAILED.\n")


	def run_ct_suite(self, module_tests_name):
		retcode, data, sterr = self.execute_os_command('%s ct suites=%s' % (self.rebar_path, module_tests_name))
		# interpret
		self.interpret_ct_test_results(retcode, data, sterr)


	def interpret_ct_test_results(self, retcode, data, sterr):
		# get outputs
		if re.search(r"DONE.", data):
			# test passed
			passed_count = re.search(r"(\d+) ok, 0 failed of \d+ test cases", data).group(1)
			self.log("\n=> %s TEST(S) PASSED.\n" % passed_count)
			return

		elif re.search(r"ERROR: One or more tests failed", data):
			self.log('\n' + data)
			failed_count = re.search(r"\d+ ok, (\d+) failed of \d+ test cases", data).group(1)
			self.log("\n=> %s TEST(S) FAILED.\n" % failed_count)
			self.log("** Hint: hit Command+Shift+C (by default) to show a browser with results. **\n")

		else:
			self.log('\n' + data)
			self.log("\n=> TEST(S) FAILED.\n")
