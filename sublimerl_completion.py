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
import os, threading, re, fnmatch
from sublimerl import SublimErlLauncher

# globals
SUBLIMERL_COMPLETIONS_ERLANG_LIBS = {}
SUBLIMERL_COMPLETIONS_ERLANG_LIBS_REBUILT = False
SUBLIMERL_COMPLETIONS_PROJECT = {}
SUBLIMERL_COMPLETIONS_PROJECT_REBUILD_IN_PROGRESS = False


# listener
class SublimErlCompletionsListener(sublime_plugin.EventListener):

	def get_available_completions(self):
		global SUBLIMERL_COMPLETIONS_ERLANG_LIBS, SUBLIMERL_COMPLETIONS_ERLANG_LIBS_REBUILT
		# load current erlang libs
		if SUBLIMERL_COMPLETIONS_ERLANG_LIBS == {}: self.load_erlang_lib_completions()
		# start rebuilding: only done once per sublimerl session
		# [i.e. needs sublime text restart to regenerate erlang completions]
		if SUBLIMERL_COMPLETIONS_ERLANG_LIBS_REBUILT == False: self.generate_erlang_lib_completions()
		# generate & load project files
		self.generate_project_completions()

	def load_erlang_lib_completions(self):
		# load completetions from file
		plugin_path = self.launcher.plugin_path()
		class SublimErlThread(threading.Thread):
			def run(self):
				disasm_filepath = os.path.join(plugin_path, "completion", "Erlang-Libs.disasm")
				if os.path.exists(disasm_filepath):
					# load file
					f = open(disasm_filepath, 'r')
					completions = f.read()
					f.close()
					# set
					global SUBLIMERL_COMPLETIONS_ERLANG_LIBS
					SUBLIMERL_COMPLETIONS_ERLANG_LIBS = eval(completions)
		SublimErlThread().start()

	def get_erlang_libs_path(self):
		completion_path = os.path.join(self.launcher.plugin_path(), "completion")
		os.chdir(completion_path)
		# run escript to get erlang lib path
		escript_command = "sublimerl_utility.erl"
		retcode, data = self.launcher.execute_os_command('%s %s' % (self.launcher.escript_path, escript_command), block=True)
		return data

	def generate_erlang_lib_completions(self):
		# rebuild
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				this.launcher.status("Regenerating Erlang lib completions...")
				# set new status
				global SUBLIMERL_COMPLETIONS_ERLANG_LIBS_REBUILT
				SUBLIMERL_COMPLETIONS_ERLANG_LIBS_REBUILT = True

				# start gen
				disasms_filepath = os.path.join(this.launcher.plugin_path(), "completion", "Erlang-Libs.disasm")
				completions_filepath = os.path.join(this.launcher.plugin_path(), "completion", "Erlang-Libs.sublime-completions")
				f_disasms = open(disasms_filepath, 'wb')
				f_completions = open(completions_filepath, 'wb')
				this.generate_completions(this.get_erlang_libs_path(), f_disasms, f_completions)
				f_disasms.close()
				f_completions.close()

				# trigger event to reload completions
				sublime.set_timeout(this.load_erlang_lib_completions, 0)
				this.launcher.status("Finished regenerating Erlang lib completions.")

		SublimErlThread().start()

	def generate_project_completions(self):
		# check lock
		global SUBLIMERL_COMPLETIONS_PROJECT_REBUILD_IN_PROGRESS
		if SUBLIMERL_COMPLETIONS_PROJECT_REBUILD_IN_PROGRESS == True: return
		# rebuild
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				this.launcher.status("Regenerating Project completions...")
				# set lock
				global SUBLIMERL_COMPLETIONS_PROJECT_REBUILD_IN_PROGRESS
				SUBLIMERL_COMPLETIONS_PROJECT_REBUILD_IN_PROGRESS = True

				# start gen
				disasms_filepath = os.path.join(this.launcher.plugin_path(), "completion", "Current-Project.disasm")
				completions_filepath = os.path.join(this.launcher.plugin_path(), "completion", "Current-Project.sublime-completions")
				f_disasms = open(disasms_filepath, 'wb')
				f_completions = open(completions_filepath, 'wb')
				this.generate_completions(this.launcher.get_project_root(), f_disasms, f_completions)
				f_disasms.close()
				f_completions.close()

				# release lock
				SUBLIMERL_COMPLETIONS_PROJECT_REBUILD_IN_PROGRESS = False
				# trigger event to reload completions
				sublime.set_timeout(this.load_project_completions, 0)
				this.launcher.status("Finished regenerating Project completions.")

		SublimErlThread().start()

	def load_project_completions(self):
		# load completetions
		plugin_path = self.launcher.plugin_path()
		class SublimErlThread(threading.Thread):
			def run(self):
				disasm_filepath = os.path.join(plugin_path, "completion", "Current-Project.disasm")
				if os.path.exists(disasm_filepath):
					# load file
					f = open(disasm_filepath, 'r')
					completions = f.read()
					f.close()
					# set
					global SUBLIMERL_COMPLETIONS_PROJECT
					SUBLIMERL_COMPLETIONS_PROJECT = eval(completions)
		SublimErlThread().start()

	def generate_completions(self, starting_dir, f_disasms, f_completions):
		disasms = []
		completions = []
		# loop directory
		for root, dirnames, filenames in os.walk(starting_dir):
			for filename in fnmatch.filter(filenames, r"*.erl"):
				if root.split('/')[-1] == 'src':
					# get module name
					module_name, module_ext = os.path.splitext(filename)
					# source file in a src directory
					filepath = os.path.join(root, filename)
					f = open(filepath, 'r')
					module = f.read()
					f.close()
					module_completions = self.get_completions(module)
					if len(module_completions) > 0:
						disasms.append("'%s': %s" % (module_name, module_completions))
						completions.append("{ \"trigger\": \"%s\", \"contents\": \"%s\" }" % (module_name, module_name))

		# write to files
		f_disasms.write("{\n" + ',\n'.join(disasms) + "\n}")
		if len(completions) > 0:
			f_completions.write("{ \"scope\": \"source.erlang\", \"completions\": [ \"erlang\",\n" + ',\n'.join(completions) + "\n]}")
		else:
			f_completions.write("")


	def get_completions(self, module):
		# get export portion in code module
		export_section = re.search(r"^\s*-\s*export\s*\(\s*\[\s*([^\]]*)\s*\]\s*\)\s*\.", module, re.DOTALL + re.MULTILINE)
		if export_section == None: return []
		# get list of exports
		exports = self.get_list_of_exports(export_section)
		if len(exports) == 0: return []
		# generate
		return self.generate_module_completions(module, exports)

	def get_list_of_exports(self, export_section):
		# loop every line and add exports
		all_exports = []
		for m in re.finditer(r"(.*)", export_section.group(1), re.MULTILINE):
			groups = m.groups()
			for i in range(0, len(groups)):
				# strip away code comments
				export = groups[i].strip().split('%')
				# strip away empty lines
				if len(export[0]) > 0:
					exports = export[0].split(',')
					for export in exports:
						export = export.strip()
						if len(export) > 0:
							all_exports.append(export)
		return all_exports

	def generate_module_completions(self, module, exports):
		completions = []
		for export in exports:
			# split param count definition
			fun = export.split('/')
			if len(fun) == 2:
				params = self.generate_params(module, fun)
				if params != None:
					completions.append((export, '%s%s' % (fun[0].strip(), params)))
		return completions

	def generate_params(self, module, fun):
		# get params count
		try: count = int(fun[1])
		except: return 
		# generate regex
		params = []
		for i in range(0, count): params.append(r"\s*([A-Z_][A-Za-z0-9_]*|.*)\s*")
		regex = fun[0].strip() + r"\s*\(" + (",".join(params)) + r"\)\s*->"
		varname_regex = r"^[A-Z][a-zA-Z0-9_]*$"
		# loop matches
		current_params = []
		for m in re.finditer(regex, module, re.MULTILINE):
			if current_params != []:
				groups = m.groups()
				for i in range(0, len(groups)):
					if not re.search(varname_regex, current_params[i]):
						# current param does not match a variable name
						if re.search(varname_regex, groups[i]):
							# if current param is a variable name
							current_params[i] = groups[i]
			else:
				current_params = list(m.groups())
		# ensure current params have variable names
		for i in range(0, len(current_params)):
			if not re.search(varname_regex, current_params[i]):
				current_params[i] = '${%d:Param%d}' % (i + 1, i + 1)
			else:
				current_params[i] = '${%d:%s}' % (i + 1, current_params[i])

		return '(' + ', '.join(current_params) + ') $%d' % (len(current_params) + 1)

	# CALLBACK ON VIEW SAVE
	def on_post_save(self, view):
		# ensure context matches
		caret = view.sel()[0].a
		if not ('source.erlang' in view.scope_name(caret) and sublime.platform() != 'windows'): return
		# init
		launcher = SublimErlLauncher(view, show_log=False, new=False)
		if launcher.available == False: return

		# compile saved file & reload completions
		generate_project_completions = self.generate_project_completions
		class SublimErlThread(threading.Thread):
			def run(self):
				# compile
				launcher.compile_source()
				# trigger event to reload completions
				sublime.set_timeout(generate_project_completions, 0)
		SublimErlThread().start()

	# CALLBACK ON VIEW ACTIVATED
	def on_activated(self, view):
		# only trigger within erlang
		caret = view.sel()[0].a
		if not ('source.erlang' in view.scope_name(caret) and sublime.platform() != 'windows'): return
		# init
		self.launcher = SublimErlLauncher(view, show_log=False, new=False)
		if self.launcher.available == False: return
		# get completions
		self.get_available_completions()

	# CALLBACK ON QUERY COMPLETIONS
	def on_query_completions(self, view, prefix, locations):
		# only trigger within erlang
		if not view.match_selector(locations[0], "source.erlang"): return []

		# only trigger if : was hit
		pt = locations[0] - len(prefix) - 1
		ch = view.substr(sublime.Region(pt, pt + 1))
		if ch != ':': return []

		# get function name that triggered the autocomplete
		function_name = view.substr(view.word(pt))
		if function_name.strip() == ':': return

		# check for existance
		global SUBLIMERL_COMPLETIONS_ERLANG_LIBS, SUBLIMERL_COMPLETIONS_PROJECT
		if SUBLIMERL_COMPLETIONS_ERLANG_LIBS.has_key(function_name): available_completions = SUBLIMERL_COMPLETIONS_ERLANG_LIBS[function_name]
		elif SUBLIMERL_COMPLETIONS_PROJECT.has_key(function_name): available_completions = SUBLIMERL_COMPLETIONS_PROJECT[function_name]
		else: return

		# return snippets
		return (available_completions, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)


