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

import sys, re, os, fnmatch, pickle, string, unittest

class SublimErlLibParser():

	def __init__(self):
		# compile default regexes
		self.regex = {
			'all': re.compile(r"(.*)", re.MULTILINE),
			'export_section': re.compile(r"^\s*-\s*export\s*\(\s*\[\s*([^\]]*)\s*\]\s*\)\s*\.", re.DOTALL + re.MULTILINE),
			'varname': re.compile(r"^[A-Z][a-zA-Z0-9_]*$"),
			'{': re.compile(r"\{.*\}"),
			'<<': re.compile(r"<<.*>>"),
			'[': re.compile(r"\[.*\]")
		}

	def strip_comments(self, code):
		# strip comments but keep the same character count
		return re.sub(re.compile(r"%(.*)\n"), lambda m: (len(m.group(0)) - 1) * ' ' + '\n', code)

	def generate_completions(self, starting_dir, dest_file_base):
		# init
		disasms = {}
		completions = []
		searches = []
		# loop directory
		rel_dirs = []
		for root, dirnames, filenames in os.walk(starting_dir):
			if 'reltool.config' in filenames:
				# found a release directory, we will ignore autocompletion for these files
				rel_dirs.append(root)
			# loop filenames ending in .erl
			for filename in fnmatch.filter(filenames, r"*.erl"):
				if '.eunit' not in root.split('/'):
					# exclude eunit files
					filepath = os.path.join(root, filename)
					# check if in release directory
					if not (True in [filepath.find(rel_dir) != -1 for rel_dir in rel_dirs]):
						# not in a release directory, get module name
						module_name, module_ext = os.path.splitext(filename)
						# get module content
						f = open(filepath, 'r')
						module = self.strip_comments(f.read())
						f.close()
						# get completions
						module_completions, line_numbers = self.get_completions(module)
						if len(module_completions) > 0:
							# set disasm
							disasms[module_name] = sorted(module_completions, key=lambda k: k[0])
							# set searches
							for i in range(0, len(module_completions)):
								function, completion = module_completions[i]
								searches.append(("%s:%s" % (module_name, function), filepath, line_numbers[i]))
							# set module completions
							completions.append("{ \"trigger\": \"%s\", \"contents\": \"%s\" }" % (module_name, module_name))

		# add BIF completions?
		if disasms.has_key('erlang'):
			# we are generating erlang disasm
			bif_completions = self.bif_completions()
			for k in bif_completions.keys():
				disasms[k].extend(bif_completions[k])
				# sort
				disasms[k] = sorted(disasms[k], key=lambda k: k[0])
			# erlang completions
			for c in bif_completions['erlang']:
				completions.append("{ \"trigger\": \"%s\", \"contents\": \"%s\" }" % (c[0], c[1]))
		else:
			# we are generating project disasm -> write to files: searches
			f_searches = open("%s.searches" % dest_file_base, 'wb')
			pickle.dump(sorted(searches, key=lambda k: k[0]), f_searches)
			f_searches.close()

		# write to files: disasms
		f_disasms = open("%s.disasm" % dest_file_base, 'wb')
		pickle.dump(disasms, f_disasms)
		f_disasms.close()
		# write to files: completions
		f_completions = open("%s.sublime-completions" % dest_file_base, 'wb')
		if len(completions) > 0:
			f_completions.write("{ \"scope\": \"source.erlang\", \"completions\": [\n" + ',\n'.join(completions) + "\n]}")
		else:
			f_completions.write("{}")
		f_completions.close()

	def get_completions(self, module):
		# get export portion in code module

		all_completions = []
		all_line_numbers = []
		for m in self.regex['export_section'].finditer(module):
			export_section = m.groups()[0]
			if export_section:
				# get list of exports
				exports = self.get_code_list(export_section)
				if len(exports) > 0:
					# add to existing completions
					completions, line_numbers = self.generate_module_completions(module, exports)
					all_completions.extend(completions)
					all_line_numbers.extend(line_numbers)
		# return all_completions
		return (all_completions, all_line_numbers)

	def bif_completions(self):
		# default BIFs not available in modules
		return {
			'erlang': [
				('abs/1', 'abs(${1:Number}) $2'),
				('atom_to_binary/2', 'atom_to_binary(${1:Atom}, ${2:Encoding}) $3'),
				('atom_to_list/1', 'atom_to_list(${1:Atom}) $2'),
				('binary_part/2', 'binary_part(${1:Subject}, ${2:PosLen}) $3'),
				('binary_part/3', 'binary_part(${1:Subject}, ${2:Start}, ${3:Length}) $4'),
				('binary_to_atom/2', 'binary_to_atom(${1:Binary}, ${2:Encoding}) $3'),
				('binary_to_existing_atom/2', 'binary_to_existing_atom(${1:Binary}, ${2:Encoding}) $3'),
				('binary_to_list/1', 'binary_to_list(${1:Binary}) $2'),
				('binary_to_list/3', 'binary_to_list(${1:Binary}, ${2:Start}, ${3:Stop}) $4'),
				('bitstring_to_list/1', 'bitstring_to_list(${1:Bitstring}) $2'),
				('binary_to_term/2', 'binary_to_term(${1:Binary}, ${2:Opts}) $3'),
				('bit_size/1', 'bit_size(${1:Bitstring}) $2'),
				('byte_size/1', 'byte_size(${1:Bitstring}) $2'),
				('check_old_code/1', 'check_old_code(${1:Module}) $2'),
				('check_process_code/2', 'check_process_code(${1:Pid}, ${2:Module}) $3'),
				('date/0', 'date() $1'),
				('delete_module/1', 'delete_module(${1:Module}) $2'),
				('demonitor/1', 'demonitor(${1:MonitorRef}) $2'),
				('demonitor/2', 'demonitor(${1:MonitorRef}, ${2:OptionList}) $3'),
				('element/2', 'element(${1:N}, ${2:Tuple}) $3'),
				('erase/0', 'erase() $1'),
				('erase/1', 'erase(${1:Key}) $2'),
				('error/1', 'error(${1:Reason}) $2'),
				('error/2', 'error(${1:Reason}, ${2:Args}) $3'),
				('exit/1', 'exit(${1:Reason}) $2'),
				('exit/2', 'exit(${1:Reason}, ${2:Args}) $3'),
				('float/1', 'float(${1:Number}) $2'),
				('float_to_list/1', 'float_to_list(${1:Float}) $2'),
				('garbage_collect/0', 'garbage_collect() $1'),
				('garbage_collect/1', 'garbage_collect(${1:Pid}) $2'),
				('get/0', 'get() $1'),
				('get/1', 'get(${1:Key}) $2'),
				('get_keys/1', 'get_keys(${1:Val}) $2'),
				('group_leader/0', 'group_leader() $1'),
				('group_leader/2', 'group_leader(${1:GroupLeader}, ${2:Pid}) $3'),
				('halt/0', 'halt() $1'),
				('halt/1', 'halt(${1:Status}) $2'),
				('halt/2', 'halt(${1:Status}, ${2:Options}) $3'),
				('hd/1', 'hd(${1:List}) $2'),
				('integer_to_list/1', 'integer_to_list(${1:Integer}) $2'),
				('iolist_to_binary/1', 'iolist_to_binary(${1:IoListOrBinary}) $2'),
				('iolist_size/1', 'iolist_size(${1:Item}) $2'),
				('is_alive/0', 'is_alive() $1'),
				('is_atom/1', 'is_atom(${1:Term}) $2'),
				('is_binary/1', 'is_binary(${1:Term}) $2'),
				('is_bitstring/1', 'is_bitstring(${1:Term}) $2'),
				('is_boolean/1', 'is_boolean(${1:Term}) $2'),
				('is_float/1', 'is_float(${1:Term}) $2'),
				('is_function/1', 'is_function(${1:Term}) $2'),
				('is_function/2', 'is_function(${1:Term}, ${2:Arity}) $3'),
				('is_integer/1', 'is_integer(${1:Term}) $2'),
				('is_list/1', 'is_list(${1:Term}) $2'),
				('is_number/1', 'is_number(${1:Term}) $2'),
				('is_pid/1', 'is_pid(${1:Term}) $2'),
				('is_port/1', 'is_port(${1:Term}) $2'),
				('is_process_alive/1', 'is_process_alive(${1:Pid}) $2'),
				('is_record/2', 'is_record(${1:Term}, ${2:RecordTag}) $3'),
				('is_record/3', 'is_record(${1:Term}, ${2:RecordTag}, ${3:Size}) $4'),
				('is_reference/1', 'is_reference(${1:Term}) $2'),
				('is_tuple/1', 'is_tuple(${1:Term}) $2'),
				('length/1', 'length(${1:List}) $2'),
				('link/1', 'link(${1:Pid}) $2'),
				('list_to_atom/1', 'list_to_atom(${1:String}) $2'),
				('list_to_binary/1', 'list_to_binary(${1:IoList}) $2'),
				('list_to_bitstring/1', 'list_to_bitstring(${1:BitstringList}) $2'),
				('list_to_existing_atom/1', 'list_to_existing_atom(${1:String}) $2'),
				('list_to_float/1', 'list_to_float(${1:String}) $2'),
				('list_to_integer/1', 'list_to_integer(${1:String}) $2'),
				('list_to_pid/1', 'list_to_pid(${1:String}) $2'),
				('list_to_tuple/1', 'list_to_tuple(${1:List}) $2'),
				('load_module/2', 'load_module(${1:Module}, ${2:Binary}) $3'),
				('make_ref/0', 'make_ref() $1'),
				('module_loaded/1', 'module_loaded(${1:Module}) $2'),
				('monitor/2', 'monitor(${1:Type}, ${2:Item}) $3'),
				('monitor_node/2', 'monitor_node(${1:Node}, ${2:Flag}) $3'),
				('node/0', 'node() $1'),
				('node/1', 'node(${1:Arg}) $2'),
				('nodes/1', 'nodes(${1:Arg}) $2'),
				('now/0', 'now() $1'),
				('open_port/2', 'open_port(${1:PortName}, ${2:PortSettings}) $3'),
				('pid_to_list/1', 'pid_to_list(${1:Pid}) $2'),
				('port_close/1', 'port_close(${1:Port}) $2'),
				('port_command/2', 'port_command(${1:Port}, ${2:Data}) $3'),
				('port_command/3', 'port_command(${1:Port}, ${2:Data}, ${3:OptionList}) $4'),
				('port_connect/2', 'port_connect(${1:Port}, ${2:Pid}) $3'),
				('port_control/3', 'port_control(${1:Port}, ${2:Operation}, ${3:Data}) $4'),
				('pre_loaded/0', 'pre_loaded() $1'),
				('process_flag/2', 'process_flag(${1:Flag}, ${2:Value}) $3'),
				('process_flag/3', 'process_flag(${1:Pid}, ${2:Flag}, ${3:Value}) $4'),
				('process_info/1', 'process_info(${1:Pid}) $2'),
				('process_info/2', 'process_info(${1:Pid}, ${2:ItemSpec}) $3'),
				('processes/0', 'processes() $1'),
				('purge_module/1', 'purge_module(${1:Module}) $2'),
				('put/2', 'put(${1:Key}, ${2:Val}) $3'),
				('register/2', 'put(${1:RegName}, ${2:PidOrPort}) $3'),
				('registered/0', 'registered() $1'),
				('round/1', 'round(${1:Number}) $2'),
				('self/0', 'self() $1'),
				('setelement/3', 'setelement(${1:Index}, ${2:Tuple1}, ${3:Value}) $4'),
				('size/1', 'size(${1:Item}) $2'),
				('spawn/3', 'spawn(${1:Module}, ${2:Function}) $3, ${3:Args}) $4'),
				('spawn_link/3', 'spawn_link(${1:Module}, ${2:Function}, ${3:Args}) $4'),
				('split_binary/2', 'split_binary(${1:Bin}, ${2:Pos}) $3'),
				('statistics/1', 'statistics(${1:Type}) $2'),
				('term_to_binary/1', 'term_to_binary(${1:Term}) $2'),
				('term_to_binary/2', 'term_to_binary(${1:Term}, ${2:Options}) $3'),
				('throw/1', 'throw(${1:Any}) $2'),
				('time/0', 'time() $1'),
				('tl/1', 'tl(${1:List1}) $2'),
				('trunc/1', 'trunc(${1:Number}) $2'),
				('tuple_size/1', 'tuple_size(${1:Tuple}) $2'),
				('tuple_to_list/1', 'tuple_to_list(${1:Tuple}) $2'),
				('unlink/1', 'unlink(${1:Id}) $2'),
				('unregister/1', 'unregister(${1:RegName}) $2'),
				('whereis/1', 'whereis(${1:RegName}) $2')
			],
			'lists': [
				('member/2', 'member(${1:Elem}, ${2:List}) $3'),
				('reverse/2', 'reverse(${1:List1}, ${2:Tail}) $3'),
				('keymember/3', 'keymember(${1:Key}, ${2:N}, ${3:TupleList}) $4'),
				('keysearch/3', 'keysearch(${1:Key}, ${2:N}, ${3:TupleList}) $4'),
				('keyfind/3', 'keyfind(${1:Key}, ${2:N}, ${3:TupleList}) $4')
			]
		}

	def generate_module_completions(self, module, exports):
		# get exports for a module

		completions = []
		line_numbers = []
		for export in exports:
			# split param count definition
			fun = export.split('/')
			if len(fun) == 2:
				# get params
				params, lineno = self.generate_params(fun, module)
				if params != None:
					# add
					completions.append((export, '%s%s' % (fun[0].strip(), params)))
					line_numbers.append(lineno)
		return (completions, line_numbers)

	def generate_params(self, fun, module):
		# generate params for a specific function name

		# get params count
		arity = int(fun[1])
		# init
		current_params = []
		lineno = 0
		# get params
		regex = re.compile(r"%s\((.*)\)\s*->" % re.escape(fun[0]), re.MULTILINE)
		for m in regex.finditer(module):
			params = m.groups()[0]
			# strip out the eventual condition part ('when')
			params = params.split('when')[0].strip()
			if params[-1:] == ')': params = params[:-1]
			# split
			params = self.split_params(params)
			if len(params) == arity:
				# function definition has the correct arity
				# get match line number if this is not a -spec line
				spec_def_pos = module.rfind('-spec', 0, m.start())
				not_a_spec_definition = spec_def_pos == -1 or len(module[spec_def_pos + 5:m.start()].strip()) > 0
				if not_a_spec_definition and lineno == 0: lineno = module.count('\n', 0, m.start()) + 1
				# add to params
				if current_params != []:
					for i in range(0, len(params)):
						if current_params[i] == '*' and self.regex['varname'].search(params[i]):
							# found a valid variable name
							current_params[i] = params[i]
				else:
					# init params
					current_params = params
		# ensure current params have variable names
		for i in range(0, len(current_params)):
			if current_params[i] == '*':
				current_params[i] = '${%d:Param%d}' % (i + 1, i + 1)
			else:
				current_params[i] = '${%d:%s}' % (i + 1, current_params[i])
		# return
		return ('(' + ', '.join(current_params) + ') $%d' % (len(current_params) + 1), lineno)

	def split_params(self, params):
		# return list of params, with proper variable name or wildcard if invalid

		# replace content of graffles with *
		params = self.regex['{'].sub("*", params)
		# replace content of <<>> with *
		params = self.regex['<<'].sub("*", params)
		# replace content of [] with *
		params = self.regex['['].sub("*", params)
		# take away comments and split per line
		params = self.get_code_list(params)
		for p in range(0, len(params)):
			# split on =
			splitted_param = params[p].split('=')
			if len(splitted_param) > 1:
				params[p] = splitted_param[1].strip()
			# spit on :: for spec declarations
			params[p] = params[p].split('::')[0]
			# convert to * where necessary
			if not self.regex['varname'].search(params[p]):
				params[p] = '*'
		# return
		return params

	def get_code_list(self, code):
		# loop every line and add code lines
		cleaned_code_list = []
		for m in self.regex['all'].finditer(code):
			groups = m.groups()
			for i in range(0, len(groups)):
				code_line = groups[i].strip()
				if len(code_line) > 0:
					code_lines = code_line.split(',')
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
			("#client{name=Name} = Client", ["Client"]),
		]
		for f in range(0, len(fixtures)):
			self.assertEqual(self.parser.split_params(fixtures[f][0]), fixtures[f][1])

	def test_generate_params(self):
		fixtures = [
			(('start', '3'),"""
							start(One, Two, Three) -> ok.

							""", ("(${1:One}, ${2:Two}, ${3:Three}) $4", 2)),
			(('start', '3'),"""
							start(One, <<>>, Three) -> ok;
							start(One, Two, Three) -> ok.

							""", ("(${1:One}, ${2:Two}, ${3:Three}) $4", 2)),
			(('start', '3'),"""
							start(One, {Abc, Cde}, Three) -> ok;
							start(One, Two, Three) -> ok.

							""", ("(${1:One}, ${2:Two}, ${3:Three}) $4", 2)),
			(('start', '3'),"""
							start(One, <<Abc:16/binary, Cde/binary>>, Three) -> ok

							""", ("(${1:One}, ${2:Param2}, ${3:Three}) $4", 2)),
			(('start', '3'),"""
							start(One, [Abc|R] = Two, Three) -> ok

							""", ("(${1:One}, ${2:Two}, ${3:Three}) $4", 2)),
			(('start', '3'),"""
							start(One, [Abc|R], Three) -> ok

							""", ("(${1:One}, ${2:Param2}, ${3:Three}) $4", 2)),
			(('start', '3'),"""
							start(One, [Abc, R], Three) -> ok

							""", ("(${1:One}, ${2:Param2}, ${3:Three}) $4", 2)),
			(('start', '3'),"""
							start(One, Two, Three, Four) -> ok.
							start(One, {Abc, Cde} = Two, Three) -> ok;
							start(One, <<>>, Three) -> ok.

							""", ("(${1:One}, ${2:Two}, ${3:Three}) $4", 3)),
			(('start', '0'),"""
							-spec start() -> ok.
							start() -> ok;
							""", ("() $1", 3)),
			(('start', '1'),"""
							start(#client{name=Name} = Client) -> ok.

							""", ("(${1:Client}) $2", 2)),
			(('start', '2'),"""
							start(Usr, Opts) when is_binary(Usr), is_list(Opts) -> ok.

							""", ("(${1:Usr}, ${2:Opts}) $3", 2)),
			(('start', '1'),"""
							start( << _:3/bytes,Body/binary >> = Data) -> ok.

							""", ("(${1:Data}) $2", 2)),
			(('start', '2'),"""
							start(Usr, Opts) when is_binary(Usr), is_list(Opts) -> ok.

							""", ("(${1:Usr}, ${2:Opts}) $3", 2)),
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
			([
				('zero/0', 'zero() $1'),
				('one/1', 'one(${1:One}) $2'),
				('two/2', 'two(${1:Two1}, ${2:Two2}) $3'),
				('three/3', 'three(${1:Three1}, ${2:Three2}, ${3:Three3}) $4'),
				('four/4', 'four(${1:Four1}, ${2:Four2}, ${3:Four3}, ${4:Four4}) $5')
			], [4, 5, 6, 7, 8])),

			("""
			-export([zero/0]).
			-export([one/1, two/2, three/3, four/4]).

			zero() -> three(Three1wrong, Three2wrong, Three3wrong).
			one(One) -> ok.
			two(Two1, Two2) -> ok.
			-spec three(ThreeParam1::list(), ThreeParam2::list(), ThreeParam3::atom()) -> ok.
			three(Three1, Three2, Three3) -> ok.
			four(Four1, <<>>, Four3, Four4) -> ok;
			four(Four1, {Four2A, Four2B, <<>>} = Four2, Four3, Four4) -> ok;
			""",
			([
				('zero/0', 'zero() $1'),
				('one/1', 'one(${1:One}) $2'),
				('two/2', 'two(${1:Two1}, ${2:Two2}) $3'),
				('three/3', 'three(${1:ThreeParam1}, ${2:ThreeParam2}, ${3:ThreeParam3}) $4'),
				('four/4', 'four(${1:Four1}, ${2:Four2}, ${3:Four3}, ${4:Four4}) $5')
			], [5, 6, 7, 9, 10]))
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

