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

import sys, re, os, fnmatch, pickle, string, unittest

class SublimErlLibParser():

	def __init__(self):
		self.regex = {
			'all': re.compile(r"(.*)", re.MULTILINE),
			'export_section': re.compile(r"^\s*-\s*export\s*\(\s*\[\s*([^\]]*)\s*\]\s*\)\s*\.", re.DOTALL + re.MULTILINE),
			'varname': re.compile(r"^[A-Z][a-zA-Z0-9_]*$"),
			'{': re.compile(r"\{.*\}"),
			'<<': re.compile(r"<<.*>>"),
			'[': re.compile(r"\[.*\]")
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
				if 'src' in root.split('/'):
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
		exports = self.get_code_list_without_comments(export_section.group(1))
		if len(exports) == 0: return []
		# generate
		return self.generate_module_completions(module, exports)

	def generate_module_completions(self, module, exports):
		completions = []
		for export in exports:
			# split param count definition
			fun = export.split('/')
			if len(fun) == 2:
				params = self.generate_params(fun, module)
				if params != None:
					completions.append((export, '%s%s' % (fun[0].strip(), params)))
		return completions

	def generate_params(self, fun, module):
		# get params count
		arity = int(fun[1])
		# init
		current_params = []
		# get params
		regex = re.compile(r"%s\((.*)\)" % fun[0], re.MULTILINE)
		for m in regex.finditer(module):
			params = m.groups()[0]
			params = self.split_params(params)
			if len(params) == arity:
				# function definition has the correct arity
				if current_params != []:
					for i in range(0, len(params)):
						if current_params[i] == '*' and self.regex['varname'].search(params[i]):
							# found a valid variable name
							current_params[i] = params[i]
				else:
					current_params = params
		# ensure current params have variable names
		for i in range(0, len(current_params)):
			if current_params[i] == '*':
				current_params[i] = '${%d:Param%d}' % (i + 1, i + 1)
			else:
				current_params[i] = '${%d:%s}' % (i + 1, current_params[i])
		# return
		return '(' + ', '.join(current_params) + ') $%d' % (len(current_params) + 1)

	def split_params(self, params):
		# replace content of graffles with *
		params = self.regex['{'].sub("*", params)
		# replace content of <<>> with *
		params = self.regex['<<'].sub("*", params)
		# replace content of [] with *
		params = self.regex['['].sub("*", params)
		# take away comments and split per line
		params = self.get_code_list_without_comments(params)
		for p in range(0, len(params)):
			# split on =
			splitted_param = params[p].split('=')
			if len(splitted_param) > 1:
				params[p] = splitted_param[1].strip()
			# convert to * where necessary
			if not self.regex['varname'].search(params[p]):
				params[p] = '*'
		# return
		return params

	def get_code_list_without_comments(self, code):
		# loop every line and add code lines
		cleaned_code_list = []
		for m in self.regex['all'].finditer(code):
			groups = m.groups()
			for i in range(0, len(groups)):
				# strip away code comments
				code_line = groups[i].strip().split('%')
				if len(code_line[0]) > 0:
					code_lines = code_line[0].split(',')
					for code_line in code_lines:
						code_line = code_line.strip()
						if len(code_line) > 0:
							cleaned_code_list.append(code_line)
		return cleaned_code_list


class TestSequenceFunctions(unittest.TestCase):

	def setUp(self):
		self.parser = SublimErlLibParser()

	def test_split_params(self):
		fixtures = [
			("One, Two, Three", ["One", "Two", "Three"]),
			("One", ["One"]),
			("One, <<>>, Three", ["One", "*", "Three"]),
			("One, [], Three", ["One", "*", "Three"]),
			("One, {TwoA, TwoB}, Three", ["One", "*", "Three"]),
			("One, {TwoA, TwoB, {TwoC, TwoD}}, Three", ["One", "*", "Three"]),
			("One, {TwoA, TwoB, {TwoC, TwoD}} = Two, Three", ["One", "Two", "Three"]),
			("One, {TwoA, TwoB, {TwoC, TwoD} = TwoE} = Two, Three", ["One", "Two", "Three"]),
			("""% comment here
				One,  % param one
				Two,  % param two

				Three % param three
			 """, ["One", "Two", "Three"])
		]
		for f in range(0, len(fixtures)):
			self.assertEqual(self.parser.split_params(fixtures[f][0]), fixtures[f][1])

	def test_generate_params(self):
		fixtures = [
			(('start', '3'),"""
							start(One, Two, Three) -> ok.

							""", "(${1:One}, ${2:Two}, ${3:Three}) $4"),
			(('start', '3'),"""
							start(One, <<>>, Three) -> ok;
							start(One, Two, Three) -> ok.

							""", "(${1:One}, ${2:Two}, ${3:Three}) $4"),
			(('start', '3'),"""
							start(One, {Abc, Cde}, Three) -> ok;
							start(One, Two, Three) -> ok.

							""", "(${1:One}, ${2:Two}, ${3:Three}) $4"),
			(('start', '3'),"""
							start(One, <<Abc:16/binary, Cde/binary>>, Three) -> ok

							""", "(${1:One}, ${2:Param2}, ${3:Three}) $4"),
			(('start', '3'),"""
							start(One, [Abc|R] = Two, Three) -> ok

							""", "(${1:One}, ${2:Two}, ${3:Three}) $4"),
			(('start', '3'),"""
							start(One, [Abc|R], Three) -> ok

							""", "(${1:One}, ${2:Param2}, ${3:Three}) $4"),
			(('start', '3'),"""
							start(One, [Abc, R], Three) -> ok

							""", "(${1:One}, ${2:Param2}, ${3:Three}) $4"),
			(('start', '3'),"""
							start(One, Two, Three, Four) -> ok.
							start(One, {Abc, Cde} = Two, Three) -> ok;
							start(One, <<>>, Three) -> ok.

							""", "(${1:One}, ${2:Two}, ${3:Three}) $4"),
		]
		for f in range(0, len(fixtures)):
			self.assertEqual(self.parser.generate_params(fixtures[f][0], fixtures[f][1]), fixtures[f][2])

	def test_get_completions(self):
		fixtures = [
			("""
			-export([zero/0, one/1, two/2, three/3, four/4]).

			zero() -> ok.
			one(One) -> ok.
			two(Two1, Two2) -> ok.
			three(Three1, Three2, Three3) -> ok.
			four(Four1, <<>>, Four3, Four4) -> ok;
			four(Four1, {Four2A, Four2B, <<>>} = Four2, Four3, Four4) -> ok;
			""",
			[
				('zero/0', 'zero() $1'),
				('one/1', 'one(${1:One}) $2'),
				('two/2', 'two(${1:Two1}, ${2:Two2}) $3'),
				('three/3', 'three(${1:Three1}, ${2:Three2}, ${3:Three3}) $4'),
				('four/4', 'four(${1:Four1}, ${2:Four2}, ${3:Four3}, ${4:Four4}) $5'),
			])
		]
		for f in range(0, len(fixtures)):
			self.assertEqual(self.parser.get_completions(fixtures[f][0]), fixtures[f][1])


if __name__ == '__main__':
	if (len(sys.argv) == 2):
		if sys.argv[1] == 'test':
			sys.argv = [sys.argv[0]]
			unittest.main()

	elif (len(sys.argv) == 3):
		starting_dir = sys.argv[1]
		dest_file_base = sys.argv[2]
		parser = SublimErlLibParser()
		parser.generate_completions(starting_dir, dest_file_base)

