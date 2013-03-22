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
import os, threading
from sublimerl_core import SUBLIMERL, SublimErlProjectLoader


# test runner
class SublimErlAutocompiler(SublimErlProjectLoader):

	def __init__(self, view):
		# init super
		SublimErlProjectLoader.__init__(self, view)
		# init
		self.panel_name = 'sublimerl_autocompiler'
		self.panel_buffer = ''
		# setup panel
		self.setup_panel()

	def setup_panel(self):
		self.panel = self.window.get_output_panel(self.panel_name)
		self.panel.settings().set("syntax", os.path.join(SUBLIMERL.plugin_path, "theme", "SublimErlAutocompile.hidden-tmLanguage"))
		self.panel.settings().set("color_scheme", os.path.join(SUBLIMERL.plugin_path, "theme", "SublimErlAutocompile.hidden-tmTheme"))

	def update_panel(self):
		if len(self.panel_buffer):
			panel_edit = self.panel.begin_edit()
			self.panel.insert(panel_edit, self.panel.size(), self.panel_buffer)
			self.panel.end_edit(panel_edit)
			self.panel.show(self.panel.size())
			self.panel_buffer = ''
			self.window.run_command("show_panel", {"panel": "output.%s" % self.panel_name})

	def hide_panel(self):
		self.window.run_command("hide_panel")

	def log(self, text):
		self.panel_buffer += text.encode('utf-8')
		sublime.set_timeout(self.update_panel, 0)

	def compile(self):
		retcode, data = self.compile_source(skip_deps=True)
		if retcode != 0:
			self.log(data)
		else:
			sublime.set_timeout(self.hide_panel, 0)

# listener
class SublimErlAutocompilerListener(sublime_plugin.EventListener):

	# CALLBACK ON VIEW SAVE
	def on_post_save(self, view):
		# check init successful
		if SUBLIMERL.initialized == False: return
		# ensure context matches
		caret = view.sel()[0].a
		if not ('source.erlang' in view.scope_name(caret) and sublime.platform() != 'windows'): return
		# init
		autocompiler = SublimErlAutocompiler(view)
		# compile saved file & reload completions
		class SublimErlThread(threading.Thread):
			def run(self):
				# compile
				autocompiler.compile()
		SublimErlThread().start()
