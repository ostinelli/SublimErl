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
import sublime, sublime_plugin
import os, threading, pickle, json, re
from sublimerl_core import SUBLIMERL, SublimErlProjectLoader

SUBLIMERL_COMPLETIONS = {
	'erlang_libs': {
		'completions': {},
		'load_in_progress': False,
		'rebuilt': False
	},
	'current_project': {
		'completions': {},
		'load_in_progress': False,
		'rebuild_in_progress': False
	}
}

# erlang module name completions
class SublimErlModuleNameCompletions():

	def set_completions(self):
		# if errors occurred
		if SUBLIMERL.plugin_path == None: return
		# load json
		completions_full_path = os.path.join(SUBLIMERL.plugin_path, 'completion', 'Erlang-Libs.sublime-completions.full')
		if os.path.exists(completions_full_path):
			f = open(completions_full_path)
			file_json = json.load(f)
			f.close()
			# filter

			completions = []
			for m in file_json['completions']:
				valid = True
				for regex in SUBLIMERL.completion_skip_erlang_libs:
					if re.search(regex, m['trigger']):
						valid = False
						break
				if valid == True: completions.append(m)
			# generate completion file
			file_json['completions'] = completions
			f = open(os.path.join(SUBLIMERL.plugin_path, 'completion', 'Erlang-Libs.sublime-completions'), 'w')
			f.write(json.dumps(file_json))
			f.close()

	def set_completions_threaded(self):
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				this.set_completions()
		SublimErlThread().start()

SublimErlModuleNameCompletions().set_completions_threaded()


# completions
class SublimErlCompletions(SublimErlProjectLoader):

	def get_available_completions(self):
		# load current erlang libs
		if SUBLIMERL_COMPLETIONS['erlang_libs']['completions'] == {}: self.load_erlang_lib_completions()
		# start rebuilding: only done once per sublimerl session
		# [i.e. needs sublime text restart to regenerate erlang completions]
		self.generate_erlang_lib_completions()
		# generate & load project files
		self.generate_project_completions()

	def get_completion_filename(self, code_type):
		if code_type == 'erlang_libs': return 'Erlang-Libs'
		elif code_type == 'current_project': return 'Current-Project'

	def load_erlang_lib_completions(self):
		self.load_completions('erlang_libs')

	def load_current_project_completions(self):
		self.load_completions('current_project')

	def load_completions(self, code_type):
		# check lock
		global SUBLIMERL_COMPLETIONS
		if SUBLIMERL_COMPLETIONS[code_type]['load_in_progress'] == True: return
		# set lock
		SUBLIMERL_COMPLETIONS[code_type]['load_in_progress'] = True
		# load
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				global SUBLIMERL_COMPLETIONS
				# load completetions from file
				disasm_filepath = os.path.join(SUBLIMERL.plugin_path, "completion", "%s.disasm" % this.get_completion_filename(code_type))
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
		class SublimErlThread(threading.Thread):
			def run(self):
				# get dirs
				dest_file_base = os.path.join(SUBLIMERL.completions_path, "Erlang-Libs")
				# get erlang libs info
				current_erlang_libs = [name for name in os.listdir(SUBLIMERL.erlang_libs_path) if os.path.isdir(os.path.join(SUBLIMERL.erlang_libs_path, name))]
				# read file of previous erlang libs
				dirinfo_path = os.path.join(SUBLIMERL.completions_path, "Erlang-Libs.dirinfo")
				if os.path.exists(dirinfo_path):
					f = open(dirinfo_path, 'rb')
					erlang_libs = pickle.load(f)
					f.close()
					if current_erlang_libs == erlang_libs:
						# same erlang libs, do not regenerate
						return
				# different erlang libs -> regenerate
				this.status("Regenerating Erlang lib completions...")
				# set cwd
				os.chdir(SUBLIMERL.support_path)
				# start gen
				this.execute_os_command("python sublimerl_libparser.py %s %s" % (this.shellquote(SUBLIMERL.erlang_libs_path), this.shellquote(dest_file_base)))
				# rename file to .full
				os.rename("%s.sublime-completions" % dest_file_base, "%s.sublime-completions.full" % dest_file_base)
				# save dir information
				f = open(dirinfo_path, 'wb')
				pickle.dump(current_erlang_libs, f)
				f.close()
				# regenerate completions based on options
				SublimErlModuleNameCompletions().set_completions()
				# trigger event to reload completions
				this.load_erlang_lib_completions()
				this.status("Finished regenerating Erlang lib completions.")

		SublimErlThread().start()

	def generate_project_completions(self):
		# check lock
		global SUBLIMERL_COMPLETIONS
		if SUBLIMERL_COMPLETIONS['current_project']['rebuild_in_progress'] == True: return
		# set lock
		SUBLIMERL_COMPLETIONS['current_project']['rebuild_in_progress'] = True

		# rebuild
		this = self
		class SublimErlThread(threading.Thread):
			def run(self):
				global SUBLIMERL_COMPLETIONS
				this.status("Regenerating Project completions...")
				# get dir
				dest_file_base = os.path.join(SUBLIMERL.completions_path, "Current-Project")
				# set cwd
				os.chdir(SUBLIMERL.support_path)
				# start gen
				this.execute_os_command("python sublimerl_libparser.py %s %s" % (this.shellquote(this.project_root), this.shellquote(dest_file_base)))
				# release lock
				SUBLIMERL_COMPLETIONS['current_project']['rebuild_in_progress'] = False
				# trigger event to reload completions
				this.load_current_project_completions()
				this.status("Finished regenerating Project completions.")

		SublimErlThread().start()


# listener
class SublimErlCompletionsListener(sublime_plugin.EventListener):

	# CALLBACK ON VIEW SAVE
	def on_post_save(self, view):
		# check init successful
		if SUBLIMERL.initialized == False: return
		# ensure context matches
		caret = view.sel()[0].a
		if not ('source.erlang' in view.scope_name(caret) and sublime.platform() != 'windows'): return
		# init
		completions = SublimErlCompletions(view)
		# compile saved file & reload completions
		class SublimErlThread(threading.Thread):
			def run(self):
				# trigger event to reload completions
				completions.generate_project_completions()
		SublimErlThread().start()

	# CALLBACK ON VIEW LOADED
	def on_load(self, view):
		# check init successful
		if SUBLIMERL.initialized == False: return
		# only trigger within erlang
		caret = view.sel()[0].a
		if not ('source.erlang' in view.scope_name(caret) and sublime.platform() != 'windows'): return
		# init
		completions = SublimErlCompletions(view)
		# get completions
		class SublimErlThread(threading.Thread):
			def run(self):
				# trigger event to reload completions
				completions.get_available_completions()
		SublimErlThread().start()

	# CALLBACK ON QUERY COMPLETIONS
	def on_query_completions(self, view, prefix, locations):
		# check init successful
		if SUBLIMERL.initialized == False: return
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
		elif SUBLIMERL_COMPLETIONS['current_project']['completions'].has_key(function_name):
			available_completions = SUBLIMERL_COMPLETIONS['current_project']['completions'][function_name]
		else: return

		# return snippets
		return (available_completions, sublime.INHIBIT_WORD_COMPLETIONS | sublime.INHIBIT_EXPLICIT_COMPLETIONS)
