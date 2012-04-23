#!/usr/bin/env escript
%% -*- erlang -*-
%%! -smp enable debug verbose
-mode(compile).

main([Basename]) ->
	gen_settings_file(Basename);

main(_) ->
	halt(1).

% "SublimErl.sublime-settings"
gen_settings_file(Basename) ->
	gen_settings_file(code:lib_dir(), Basename).
gen_settings_file(SearchPath, Basename) ->
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
	{ok, CompletionsFile} = file:open(Basename ++ ".sublime-completions", [write, raw]),
	CompletionsFileContents = string:join(ModuleCompletions, ",\n"),
	file:write(CompletionsFile, "{ \"scope\": \"source.erlang\", \"completions\": [ \"erlang\", \n" ++ CompletionsFileContents ++ "\n]}"),
	file:close(CompletionsFile).

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
	"('" ++ FunctionName ++ "/" ++ integer_to_list(Count) ++ "', '" ++ FunctionName ++ Params ++ " ->\\n\\t$" ++ integer_to_list(Count + 1) ++ "')".


