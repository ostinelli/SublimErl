import sublime, sublime_plugin
import sys, os, re, subprocess

SUBLIMERL_VERSION = '0.1'

class SublimErlCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		# init
		self.panel = SublimErlPanel(self.view)
		self.cmd = SublimErlOsCommands(self)
		# start
		self.main()


	def main(self):
		self.log("Starting tests (SublimErl v%s).\n" % SUBLIMERL_VERSION)

		# is this a test module?
		module_name = self.get_target_module_name()
		if module_name == None:
			self.log_error("This isn't an Eunit test module (declared module name doesn't end in _tests, or cannot find module declaration).")
			return
		module_filename = "%s.erl" % module_name
		module_tests_filename = "%s_tests.erl" % module_name

		# get root OTP project's root die
		project_root_dir = self.get_otp_project_root(module_tests_filename)
		if project_root_dir == None: return
		project_src_dir = os.path.join(project_root_dir, 'src')

		# set current directory to root - needed by rebar
		os.chdir(os.path.abspath(project_root_dir))

		# rebar check
		if self.rebar_exists() == False:
			self.log_error("Rebar cannot be found, please download and install from <https://github.com/basho/rebar>.")
			return

		# test for target file existance
		module_filepath = os.path.join(project_src_dir, module_filename)
		if os.path.exists(module_filepath) == False:
			self.log_error("Target file \"%s\" could not be found." % module_filepath)
			return

		# get function name depending on cursor position
		function_name = self.get_test_function_name()
		if function_name == None:
			self.log_error("Cannot get test function name: cursor is not scoped to a test function.")
			return

		# create test object & run tests
		sublimerl_test = SublimErlTestInfo(module_filename, module_tests_filename, function_name, project_root_dir, project_src_dir, self)
		sublimerl_test.run_single_test()


	def get_otp_project_root(self, module_tests_filename):
		filename = self.view.file_name()
		if filename == None:
			self.log_error("This module (\"%s\") has not been saved on disk: cannot retrieve project root." % module_tests_filename)
			return

		# get project root
		project_root_path_arr = os.path.dirname(filename).split(os.sep)
		project_root_path_arr.pop()
		self.project_root_path = os.sep.join(project_root_path_arr)

		return self.project_root_path


	def get_target_module_name(self):
		# find module declaration and get target module name
		module_region = self.view.find(r"^\s*-module\((?:[a-zA-Z0-9_]+)_tests\)\.", 0)
		if module_region != None:
			return re.match(r"^\s*-module\(([a-zA-Z0-9_]+)_tests\)\.", self.view.substr(module_region)).group(1)	


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
		return self.cmd.rebar_exists()


	def log(self, text):
		self.panel.write_to_panel(text)

	def log_error(self, text):
		self.log("Error => %s\n[ABORTED]\n" % text)


class SublimErlPanel():

	def __init__(self, view):
		# init
		self.window = view.window()
		# create panel
		self.panel_name = 'sublimerl_panel'
		self.output_panel = self.window.get_output_panel(self.panel_name)


	def write_to_panel(self, text):
		# output to the panel
		panel = self.output_panel
		panel_edit = panel.begin_edit()
		panel.insert(panel_edit, panel.size(), text)
		panel.end_edit(panel_edit)
		panel.show(panel.size())

		self.window.run_command("show_panel", {"panel": "output." + self.panel_name})


class SublimErlTestInfo():

	def __init__(self, module_filename, module_tests_filename, function_name, project_root_dir, project_src_dir, parent):
		# save
		self.module_filename = module_filename
		self.module_tests_filename = module_tests_filename
		self.function_name = function_name
		self.project_root_dir = project_root_dir
		self.project_src_dir = project_src_dir
		# logs
		self.log = parent.log
		self.log_error = parent.log_error


	def run_single_test(self):
		self.log("Running test \"%s\" for target module \"%s\".\n" % (self.function_name, self.module_filename))
		self.compile_all()


	def compile_all(self):
		pass


class SublimErlOsCommands():

	def __init__(self, parent):
		# logs
		self.log = parent.log
		self.log_error = parent.log_error

		# get rebar path
		self.rebar_path = self.get_rebar_path()
		


	# def set_env(self):
	# 	# get user .bash_profile
	# 	bash_profile = os.path.join(os.getenv('HOME'), '.bash_profile')

	# 	self.log(os.getenv('PATH'))
	# 	if os.path.exists(bash_profile):
	# 		# source
	# 		p = subprocess.Popen(". %s; env" % bash_profile, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
	# 		data, stderr = p.communicate()
	# 		env = dict((line.split("=", 1) for line in data.splitlines()))
			# TODO: SYSTEM LEAKS!!
			# os.putenv('PATH', env['PATH'] + ':/usr/local/bin')


	def execute_os_command(self, os_cmd):
		p = subprocess.Popen(os_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
		stdout, stderr = p.communicate()
		return (p.returncode, stdout, stderr)


	def rebar_exists(self):
		return self.rebar_path != None


	def get_rebar_path(self):
		retcode, data, sterr = self.execute_os_command('which rebar')
		if retcode != 0 or len(data) > 0:
			return data.strip()



