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
import os, time, threading, pickle
from sublimerl_core import SUBLIMERL, SublimErlTextCommand, SublimErlProjectLoader
from sublimerl_completion import SUBLIMERL_COMPLETIONS


# main autoformat
class SublimErlFunctionSearch():

	def __init__(self, view):
		# init
		self.view = view
		self.window = view.window()
		self.search_completions = []

	def show(self):
		# get completions
		self.set_search_completions()
		# strip out just the function name to be displayed
		completions = []
		for name, filepath, lineno in self.search_completions:
			completions.append(name)
		# open quick panel
		sublime.active_window().show_quick_panel(completions, self.on_select)

	def set_search_completions(self):
		# load file
		searches_filepath = os.path.join(SUBLIMERL.plugin_path, "completion", "Current-Project.searches")
		f = open(searches_filepath, 'r')
		searches = pickle.load(f)
		f.close()
		self.search_completions = searches

	def on_select(self, index):
		# get file and line
		name, filepath, lineno = self.search_completions[index]
		# open module at function position
		self.open_file_and_goto_line(filepath, lineno)

	def open_file_and_goto_line(self, filepath, line):
		# open file
		self.new_view = self.window.open_file(filepath)
		# wait until file is loaded before going to the appropriate line
		this = self
		self.check_file_loading()
		class SublimErlThread(threading.Thread):
			def run(self):
				# wait until file has done loading
				s = 0
				while this.is_loading and s < 3:
					time.sleep(0.1)
					sublime.set_timeout(this.check_file_loading, 0)
					s += 1
				# goto line
				def goto_line():
					# goto line
					this.new_view.run_command("goto_line", {"line": line} )
					# remove unused attrs
					del this.new_view
					del this.is_loading
				if not this.is_loading: sublime.set_timeout(goto_line, 0)

		SublimErlThread().start()

	def check_file_loading(self):
		self.is_loading = self.new_view.is_loading()


# repeat last test
class SublimErlFunctionSearchCommand(SublimErlTextCommand):
	def run_command(self, edit):
		search = SublimErlFunctionSearch(self.view)
		search.show()
