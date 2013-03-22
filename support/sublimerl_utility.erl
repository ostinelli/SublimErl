#!/usr/bin/env escript
%% -*- erlang -*-
%%! -smp enable debug verbose
%% ==========================================================================================================
%% SublimErl - A Sublime Text 2 Plugin for Erlang Integrated Testing & Code Completion
%%
%% Copyright (C) 2013, Roberto Ostinelli <roberto@ostinelli.net>, code for indenting taken and adapted from
%%    <https://github.com/jimenezrick/vimerl/blob/master/indent/erlang_indent.erl> by Ricardo Catalinas
%%    Jiménez, who has agreed to release this portion of code in BSD license.
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
main(["lib_dir"]) ->
	io:format("~s", [code:lib_dir()]);
main(_) ->
	halt(1).
