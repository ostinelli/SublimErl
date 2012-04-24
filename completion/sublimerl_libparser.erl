#!/usr/bin/env escript
%% -*- erlang -*-
%%! -smp enable debug verbose
%% ==========================================================================================================
%% SublimErl - A Sublime Text 2 Plugin for Erlang Integrated Testing & Code Completion
%% 
%% Copyright (C) 2012, Roberto Ostinelli <roberto@ostinelli.net>.
%% All rights reserved.
%%
%% BSD License
%% 
%% Redistribution and use in source and binary forms, with or without modification, are permitted provided
%% that the following conditions are met:
%%
%%  * Redistributions of source code must retain the above copyright notice, this list of conditions and the
%%        following disclaimer.
%%  * Redistributions in binary form must reproduce the above copyright notice, this list of conditions and
%%        the following disclaimer in the documentation and/or other materials provided with the distribution.
%%  * Neither the name of the authors nor the names of its contributors may be used to endorse or promote
%%        products derived from this software without specific prior written permission.
%%
%% THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND ANY EXPRESS OR IMPLIED
%% WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A
%% PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE FOR
%% ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED
%% TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
%% HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING
%% NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
%% POSSIBILITY OF SUCH DAMAGE.
%% ==========================================================================================================
-mode(compile).

% command line exposure
main([Basename]) ->
	gen_completion_files(Basename);

main([Basename, SearchPath]) ->
	gen_completion_files(Basename, SearchPath);

main(_) ->
	halt(1).

% generate files
gen_completion_files(Basename) ->
	gen_completion_files(Basename, code:lib_dir()).
gen_completion_files(Basename, SearchPath) ->
	% loop all beam files
	F = fun(FilePath, {AccModules, AccDisasm}) ->
		% get exports
		{beam_file, ModuleName, Exported0, _, _, _} = beam_disasm:file(FilePath),
		Exports = [{Name, Arity} || {Name, Arity, _} <- Exported0],
		% add to list
		ModuleNameStr = atom_to_list(ModuleName),
		{
			[io_lib:format("{ \"trigger\": \"~s\", \"contents\": \"~s\" }", [ModuleNameStr, ModuleNameStr]) | AccModules],
			[io_lib:format("'~s': [~s]", [ModuleNameStr, gen_snippets(Exports)]) | AccDisasm]
		}
	end,
	{ModuleCompletions, DisasmExports} = filelib:fold_files(SearchPath, ".*\\.beam", true, F, {[], []}),
	% write to .lib-disasm file
	{ok, DisasmFile} = file:open(Basename ++ ".disasm", [write, raw]),
	DisasmFileContents = string:join(DisasmExports, ",\n"),
	file:write(DisasmFile, "{\n" ++ DisasmFileContents ++ "\n}"),
	file:close(DisasmFile),
	% write to .sublime-completions file
	case ModuleCompletions of
		[] ->
			ok;
		_ ->
			{ok, CompletionsFile} = file:open(Basename ++ ".sublime-completions", [write, raw]),
			CompletionsFileContents = string:join(ModuleCompletions, ",\n"),
			file:write(CompletionsFile, "{ \"scope\": \"source.erlang\", \"completions\": [ \"erlang\", \n" ++ CompletionsFileContents ++ "\n]}"),
			file:close(CompletionsFile)
	end.

% generate all snippets for the exports
gen_snippets(Exports) ->
	F = fun({Function, Count}, Acc) ->
		[gen_params_snippet(atom_to_list(Function), Count) | Acc]
	end,
	Snippets = lists:reverse(lists:foldl(F, [], Exports)),
	string:join(Snippets, ", ").

% gen parameters snippet
gen_params_snippet(FunctionName, 0) ->
	params_snippet(FunctionName, "()", 0);
gen_params_snippet(FunctionName, Count) ->
	% build params
	F = fun(C, Acc) ->
		["$" ++ integer_to_list(C) | Acc]
	end,
	Params0 = lists:reverse(lists:foldl(F, [], lists:seq(1, Count))),
	Params = "(" ++ string:join(Params0, ", ") ++ ")",
	% build snippet
	params_snippet(FunctionName, Params, Count).
params_snippet(FunctionName, Params, Count) ->
	"('" ++ FunctionName ++ "/" ++ integer_to_list(Count) ++ "', '" ++ FunctionName ++ Params ++ " $" ++ integer_to_list(Count + 1) ++ "')".


