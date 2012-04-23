#!/usr/bin/env escript
%% -*- erlang -*-
%%! -smp enable debug verbose
-mode(compile).

main([SettingsFileName]) ->
	gen_settings_file(SettingsFileName);

main(_) ->
	halt(1).

% "SublimErl.sublime-settings"
gen_settings_file(SettingsFileName) ->
	gen_settings_file(code:lib_dir(), SettingsFileName).
gen_settings_file(SearchPath, SettingsFileName) ->
	% loop all beam files
	F = fun(FilePath, Acc) ->
		% get exports
		{beam_file, ModuleName, Exported0, _, _, _} = beam_disasm:file(FilePath),
		Exports = [{Name, Arity} || {Name, Arity, _} <- Exported0],
		% add to list
		[io_lib:format("'~s': [~s]", [atom_to_list(ModuleName), gen_snippets(Exports)]) | Acc]
	end,
	ModuleExports = filelib:fold_files(SearchPath, ".*\\.beam", true, F, []),
	FileContents = string:join(ModuleExports, ",\n"),
	% write to file
	{ok, ResultFile} = file:open(SettingsFileName, [write, raw]),
	file:write(ResultFile, "{\n" ++ FileContents ++ "\n}"),
	file:close(ResultFile).

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


