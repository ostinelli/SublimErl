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
import os, threading
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
		global SUBLIMERL_COMPLETIONS_PROJECT

		# load erlang libs
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

	def generate_erlang_lib_completions(self):
		launcher = self.launcher
		load_erlang_lib_completions = self.load_erlang_lib_completions
		class SublimErlThread(threading.Thread):
			def run(self):
				# set new status
				global SUBLIMERL_COMPLETIONS_ERLANG_LIBS_REBUILT
				SUBLIMERL_COMPLETIONS_ERLANG_LIBS_REBUILT = True
				# change cwd - TODO: check that this doesn't interfere with other plugins
				completion_path = os.path.join(launcher.plugin_path(), "completion")
				os.chdir(completion_path)
				# run escript to get all erlang lib exports
				escript_command = "sublimerl_libparser.erl \"Erlang-Libs\""
				retcode, data = launcher.execute_os_command('%s %s' % (launcher.escript_path, escript_command))
				# trigger event to reload completions
				sublime.set_timeout(load_erlang_lib_completions, 0)
		SublimErlThread().start()

	def generate_project_completions(self):
		# check lock
		global SUBLIMERL_COMPLETIONS_PROJECT_REBUILD_IN_PROGRESS
		if SUBLIMERL_COMPLETIONS_PROJECT_REBUILD_IN_PROGRESS == True: return
		# rebuild
		launcher = self.launcher
		load_project_completions = self.load_project_completions
		class SublimErlThread(threading.Thread):
			def run(self):
				# set lock
				global SUBLIMERL_COMPLETIONS_PROJECT_REBUILD_IN_PROGRESS
				SUBLIMERL_COMPLETIONS_PROJECT_REBUILD_IN_PROGRESS = True
				# change cwd - TODO: check that this doesn't interfere with other plugins
				completion_path = os.path.join(launcher.plugin_path(), "completion")
				os.chdir(completion_path)
				# run escript to get all erlang lib exports
				escript_command = "sublimerl_libparser.erl \"Current-Project\" \"%s\"" % launcher.get_project_root()
				retcode, data = launcher.execute_os_command('%s %s' % (launcher.escript_path, escript_command))
				# release lock
				SUBLIMERL_COMPLETIONS_PROJECT_REBUILD_IN_PROGRESS = False
				# trigger event to reload completions
				sublime.set_timeout(load_project_completions, 0)
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


