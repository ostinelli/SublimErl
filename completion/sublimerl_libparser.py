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

import sys, re, os, fnmatch, pickle

class SublimErlLibParser():

	def __init__(self):
		self.regex = {
			'all': re.compile(r"(.*)", re.MULTILINE),
			'export_section': re.compile(r"^\s*-\s*export\s*\(\s*\[\s*([^\]]*)\s*\]\s*\)\s*\.", re.DOTALL + re.MULTILINE),
			'varname': re.compile(r"^[A-Z][a-zA-Z0-9_]*$")
		}

	def generate_completions(self, starting_dir, dest_file_base):
		disasms = {}
		completions = []
		# loop directory
		rel_dirs = []
		for root, dirnames, filenames in os.walk(starting_dir):
			if 'reltool.config' in filenames:
				# find a release directory, ignore autocompletion for these files
				rel_dirs.append(root)
			for filename in fnmatch.filter(filenames, r"*.erl"):
				if root.split('/')[-1] == 'src':
					# source file in a src directory
					filepath = os.path.join(root, filename)
					# check if in release directory
					if not (True in [filepath.find(rel_dir) != -1 for rel_dir in rel_dirs]):
						# not in a release directory, get module name
						module_name, module_ext = os.path.splitext(filename)
						f = open(filepath, 'r')
						module = f.read()
						f.close()
						module_completions = self.get_completions(module)
						if len(module_completions) > 0:
							disasms[module_name] = module_completions
							completions.append("{ \"trigger\": \"%s\", \"contents\": \"%s\" }" % (module_name, module_name))

		# write to files: disasms
		f_disasms = open("%s.disasm" % dest_file_base, 'wb')
		pickle.dump(disasms, f_disasms)
		f_disasms.close()
		# write to files: completions
		f_completions = open("%s.sublime-completions" % dest_file_base, 'wb')
		if len(completions) > 0:
			f_completions.write("{ \"scope\": \"source.erlang\", \"completions\": [ \"erlang\",\n" + ',\n'.join(completions) + "\n]}")
		else:
			f_completions.write("")
		f_completions.close()

	def get_completions(self, module):
		# get export portion in code module
		export_section = self.regex['export_section'].search(module)
		if export_section == None: return []
		# get list of exports
		exports = self.get_list_of_exports(export_section)
		if len(exports) == 0: return []
		# generate
		return self.generate_module_completions(module, exports)

	def get_list_of_exports(self, export_section):
		# loop every line and add exports
		all_exports = []
		for m in self.regex['all'].finditer(export_section.group(1)):
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
		regex = re.compile(regex, re.MULTILINE)

		# loop matches
		current_params = []
		for m in regex.finditer(module):
			if current_params != []:
				groups = m.groups()
				for i in range(0, len(groups)):
					if not self.regex['varname'].search(current_params[i]):
						# current param does not match a variable name
						if self.regex['varname'].search(groups[i]):
							# if current param is a variable name
							current_params[i] = groups[i]
			else:
				current_params = list(m.groups())

		# ensure current params have variable names
		for i in range(0, len(current_params)):
			if not self.regex['varname'].search(current_params[i]):
				current_params[i] = '${%d:Param%d}' % (i + 1, i + 1)
			else:
				current_params[i] = '${%d:%s}' % (i + 1, current_params[i])

		return '(' + ', '.join(current_params) + ') $%d' % (len(current_params) + 1)


if __name__ == '__main__':
	if (len(sys.argv) == 3):
		starting_dir = sys.argv[1]
		dest_file_base = sys.argv[2]
		parser = SublimErlLibParser()
		parser.generate_completions(starting_dir, dest_file_base)


