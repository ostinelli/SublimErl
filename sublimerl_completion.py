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
import os, threading, re, fnmatch, pickle
from sublimerl import SublimErlLauncher

# globals
SUBLIMERL_COMPLETIONS = {
	'erlang_libs': {
		'completions': {},
		'load_in_progress': False,
		'rebuilt': False
	},
	'project': {
		'completions': {},
		'load_in_progress': False,
		'rebuild_in_progress': False		
	}
}

# listener
class SublimErlCompletionsListener(sublime_plugin.EventListener):

	def get_available_completions(self):
		# load current erlang libs
		global SUBLIMERL_COMPLETIONS
		if SUBLIMERL_COMPLETIONS['erlang_libs']['completions'] == {}:	self.load_erlang_lib_completions()
		# start rebuilding: only done once per sublimerl session
		# [i.e. needs sublime text restart to regenerate erlang completions]
		self.generate_erlang_lib_completions()
		# generate & load project files
		self.generate_project_completions()

	def get_completion_filename(self, code_type):
		if code_type == 'erlang_libs': return 'Erlang-Libs'
		elif code_type == 'project': return 'Current-Project'

	def load_erlang_lib_completions(self):
		self.load_completions('erlang_libs')

	def load_project_completions(self):
		self.load_completions('project')

	def load_completions(self, code_type):
		# check lock
		global SUBLIMERL_COMPLETIONS
		if SUBLIMERL_COMPLETIONS[code_type]['load_in_progress'] == True: return
		# set lock
		SUBLIMERL_COMPLETIONS[code_type]['load_in_progress'] = True
		# load
		this = self
		plugin_path = this.launcher.plugin_path()
		class SublimErlThread(threading.Thread):
			def run(self):
				global SUBLIMERL_COMPLETIONS

				# load completetions from file
				disasm_filepath = os.path.join(plugin_path, "completion", "%s.disasm" % this.get_completion_filename(code_type))
				if os.path.exists(disasm_filepath):
					# load file
					f = open(disasm_filepath, 'r')
					completions = pickle.load(f)
					f.close()
					# set
					SUBLIMERL_COMPLETIONS[code_type]['completions'] = completions

				# release lock
				SUBLIMERL_COMPLETIONS[code_type]['load_in_progress'] = False

		SublimErlThread().start()

	def generate_erlang_lib_completions(self):
		# check lock
		global SUBLIMERL_COMPLETIONS
		if SUBLIMERL_COMPLETIONS['erlang_libs']['rebuilt'] == True: return
		# set lock
		SUBLIMERL_COMPLETIONS['erlang_libs']['rebuilt'] = True

		# rebuild
		this = self
		plugin_path = this.launcher.plugin_path()
		class SublimErlThread(threading.Thread):
			def run(self):
				# get dirs
				erlang_lib_path = this.get_erlang_libs_path()
				completions_path = os.path.join(plugin_path, "completion")
				dest_file_base = os.path.join(completions_path, "Erlang-Libs")
				# get erlang libs info
				current_erlang_libs = [name for name in os.listdir(erlang_lib_path) if os.path.isdir(os.path.join(erlang_lib_path, name))]
				# read file of previous erlang libs
				dirinfo_path = os.path.join(completions_path, "Erlang-Libs.dirinfo")
				if os.path.exists(dirinfo_path):
					f = open(dirinfo_path, 'rb')
					erlang_libs = pickle.load(f)
					f.close()
					if current_erlang_libs == erlang_libs:
						# same erlang libs, do not regenerate
						return
				# different erlang libs -> regenerate
				this.launcher.status("Regenerating Erlang lib completions...")
				# set cwd
				os.chdir(completions_path)
				# start gen
				this.launcher.execute_os_command("python sublimerl_libparser.py %s %s" % (this.launcher.shellquote(erlang_lib_path), this.launcher.shellquote(dest_file_base)))
				# save dir information
				f = open(dirinfo_path, 'wb')
				pickle.dump(current_erlang_libs, f)
				f.close()
				# trigger event to reload completions
				sublime.set_timeout(this.load_erlang_lib_completions, 0)
				this.launcher.status("Finished regenerating Erlang lib completions.")

		SublimErlThread().start()

	def generate_project_completions(self):
		# check lock
		global SUBLIMERL_COMPLETIONS
		if SUBLIMERL_COMPLETIONS['project']['rebuild_in_progress'] == True: return
		# set lock
		SUBLIMERL_COMPLETIONS['project']['rebuild_in_progress'] = True

		# rebuild
		this = self
		plugin_path = this.launcher.plugin_path()
		class SublimErlThread(threading.Thread):
			def run(self):
				this.launcher.status("Regenerating Project completions...")
				# get dirs
				starting_dir = this.launcher.get_project_root()
				completions_path = os.path.join(plugin_path, "completion")
				dest_file_base = os.path.join(completions_path, "Current-Project")
				# set cwd
				os.chdir(completions_path)
				# start gen
				this.launcher.execute_os_command("python sublimerl_libparser.py %s %s" % (this.launcher.shellquote(starting_dir), this.launcher.shellquote(dest_file_base)))
				# release lock
				global SUBLIMERL_COMPLETIONS
				SUBLIMERL_COMPLETIONS['project']['rebuild_in_progress'] = False
				# trigger event to reload completions
				sublime.set_timeout(this.load_project_completions, 0)
				this.launcher.status("Finished regenerating Project completions.")

		SublimErlThread().start()

	def get_erlang_libs_path(self):
		completion_path = os.path.join(self.launcher.plugin_path(), "completion")
		os.chdir(completion_path)
		# run escript to get erlang lib path
		escript_command = "sublimerl_utility.erl lib_dir"
		retcode, data = self.launcher.execute_os_command('%s %s' % (self.launcher.escript_path, escript_command), block=True)
		return data

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

	# CALLBACK ON VIEW LOADED
	def on_load(self, view):
		# only trigger within erlang
		caret = view.sel()[0].a
		if not ('source.erlang' in view.scope_name(caret) and sublime.platform() != 'windows'): return
		# init
		self.launcher = SublimErlLauncher(view, show_log=False, new=False)
		if self.launcher.available == False: return
		# get completions
		get_available_completions = self.get_available_completions
		class SublimErlThread(threading.Thread):
			def run(self):
				# trigger event to reload completions
				sublime.set_timeout(get_available_completions, 0)
		SublimErlThread().start()

	# CALLBACK ON QUERY COMPLETIONSasc
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
		global SUBLIMERL_COMPLETIONS
		if SUBLIMERL_COMPLETIONS['erlang_libs']['completions'].has_key(function_name):
			available_completions = SUBLIMERL_COMPLETIONS['erlang_libs']['completions'][function_name]
		elif SUBLIMERL_COMPLETIONS['project']['completions'].has_key(function_name):
			available_completions = SUBLIMERL_COMPLETIONS['project']['completions'][function_name]
		else: return

		# return snippets
		return (available_completions, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)


