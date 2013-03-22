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

% macros
-define(IS(T, C), (element(1, T) == C)).
-define(OPEN_BRACKET(T), ?IS(T, '('); ?IS(T, '{'); ?IS(T, '['); ?IS(T, '<<')).
-define(CLOSE_BRACKET(T), ?IS(T, ')'); ?IS(T, '}'); ?IS(T, ']'); ?IS(T, '>>')).
-define(BRANCH_EXPR(T), ?IS(T, 'fun'); ?IS(T, 'receive'); ?IS(T, 'if'); ?IS(T, 'case'); ?IS(T, 'try')).
-record(state, {stack = [], tabs = [0], cols = [none]}).

% command line exposure
main([FilePath]) ->
	Lines = read_file(FilePath),
	Formatted = source_indentation(Lines),
	io:format("~s", [Formatted]);

main(_) ->
	halt(1).

read_file(File) ->
    {ok, FileDev} = file:open(File, [raw, read, read_ahead]),
	Lines = read_file([],FileDev),
    file:close(FileDev),
    Lines.

read_file(Lines, FileDev) ->
     case file:read_line(FileDev) of
          {ok, Line} ->
               read_file([Line|Lines], FileDev);
          eof ->
               lists:reverse(Lines)
     end.

source_indentation(Lines) ->
    try
    	Source = lists:flatten(Lines),
        Tokens = tokenize_source(Source),
        lists:flatten(source_indentation(Tokens, Lines, 1, []))
    catch
        throw:scan_error ->
            {-1, none}
    end.

source_indentation(_Tokens, [], _Pos, FormattedLines) ->
	lists:reverse(FormattedLines);
source_indentation(Tokens, [Line|Lines], Pos, FormattedLines) ->
    try
        % compute indent for line in Pos
        {PrevToks, NextToks} = split_prev_block(Tokens, Pos),
        {IndentTab, _IndentCol} = indentation_between(PrevToks, NextToks),
        % reformat line
        NewLine = string:copies("\t", IndentTab) ++
        	re:replace(Line, "\\A[ \t]+", "", [{return, list}]),
        source_indentation(Tokens, Lines, Pos + 1, [NewLine|FormattedLines])
    catch
        throw:scan_error ->
            {-1, none}
    end.

tokenize_source(Source) ->
    eat_shebang(tokenize_source2(Source)).

tokenize_source2(Source) ->
    case erl_scan:string(Source, {1, 1}) of
        {ok, Tokens, _} ->
            Tokens;
        {error, _, _} ->
            throw(scan_error)
    end.

eat_shebang([{'#', {N, _}}, {'!', {N, _}} | Tokens]) ->
    lists:dropwhile(fun(T) -> line(T) == N end, Tokens);
eat_shebang(Tokens) ->
    Tokens.

split_prev_block(Tokens, Line) when Line < 1 ->
    error(badarg, [Tokens, Line]);
split_prev_block(Tokens, Line) ->
    {PrevToks, NextToks} = lists:splitwith(fun(T) -> line(T) < Line end, Tokens),
    PrevToks2 = lists:reverse(PrevToks),
    PrevToks3 = lists:takewhile(fun(T) -> category(T) /= dot end, PrevToks2),
    {lists:reverse(PrevToks3), NextToks}.

category(Token) ->
    {category, Cat} = erl_scan:token_info(Token, category),
    Cat.

line(Token) ->
    {line, Line} = erl_scan:token_info(Token, line),
    Line.

column(Token) ->
    {column, Col} = erl_scan:token_info(Token, column),
    Col.

indentation_between([], _) ->
    {0, none};
indentation_between(PrevToks, NextToks) ->
    try
        State = parse_tokens(PrevToks),
        State2 = case State#state.stack of
            [{'=', _} | _] ->
                pop(State);
            _ ->
                State
        end,
        #state{tabs = [Tab | _], cols = [Col | _]} = State,
        Tab2 = hd(State2#state.tabs),
        case {State2#state.stack, NextToks} of
            {_, [T | _]} when ?CLOSE_BRACKET(T) ->
                case Col of
                    none ->
                        {Tab, Col};
                    _ when ?IS(T, '>>') ->
                        {Tab, Col - 2};
                    _ ->
                        {Tab, Col - 1}
                end;
            {[{'try', _} | _], [T | _]} when ?IS(T, 'catch'); ?IS(T, 'after') ->
                {Tab2 - 1, none};
            {[{'receive', _} | _], [T | _]} when ?IS(T, 'after') ->
                {Tab2 - 1, none};
            {[{'->', _}, {'try', _} | _], [T | _]} when ?IS(T, 'catch') ->
                {Tab2 - 2, none};
            {[{'->', _} | _], [T | _]} when ?IS(T, 'after') ->
                {Tab2 - 2, none};
            {[T1 | _], [T2 | _]} when ?IS(T1, 'begin'), ?IS(T2, 'end') ->
                {Tab2 - 1, none};
            {[T1 | _], [T2 | _]} when ?IS(T1, 'try'), ?IS(T2, 'end') ->
                {Tab2 - 1, none};
            {[T1 | _], [T2 | _]} when ?IS(T1, '->'), ?IS(T2, 'end') ->
                {Tab2 - 2, none};
            {_, [T | _]} when ?IS(T, 'of') ->
                {Tab2 - 1, none};
            _ ->
                {Tab, Col}
        end
    catch
        throw:{parse_error, LastToks, LastState, _Line} ->
            case LastToks of
                [] ->
                    _LastTok = eof;
                [_LastTok | _] ->
                    _LastTok
            end,
            {hd(LastState#state.tabs), hd(LastState#state.cols)}
    end.

parse_tokens(Tokens = [{'-', _} | _]) ->
    parse_attribute(Tokens, #state{});
parse_tokens(Tokens = [{atom, _, _} | _]) ->
    parse_function(Tokens, #state{});
parse_tokens(Tokens) ->
    throw({parse_error, Tokens, #state{}, ?LINE}).

parse_attribute([T = {'-', _}, {atom, _, export} | Tokens], State = #state{stack = []}) ->
    parse_next(Tokens, push(State, T, -1));
parse_attribute([T1 = {'-', _}, T2, T3 | Tokens], State = #state{stack = []}) when ?IS(T2, atom), ?IS(T3, atom) ->
    parse_next(Tokens, push(State, T1, 1));
parse_attribute([T = {'-', _} | Tokens], State = #state{stack = []}) ->
    parse_next(Tokens, push(State, T, 0));
parse_attribute(Tokens, State) ->
    throw({parse_error, Tokens, State, ?LINE}).

parse_function([T = {atom, _, _} | Tokens], State = #state{stack = []}) ->
    parse_next(Tokens, indent(push(State, T, 1), 1));
parse_function([], State) ->
    State;
parse_function(Tokens, State) ->
    throw({parse_error, Tokens, State, ?LINE}).

parse_next(Tokens, State) ->
    parse_next2(next_relevant_token(Tokens), State).

parse_next2([T | Tokens], State) when ?IS(T, '<<') ->
    case same_line(T, Tokens) of
        true ->
            parse_next(Tokens, push(State, T, 1, column(T) + 1));
        false ->
            parse_next(Tokens, push(State, T, 1))
    end;
parse_next2([T | Tokens], State) when ?OPEN_BRACKET(T) ->
    case same_line(T, Tokens) of
        true ->
            parse_next(Tokens, push(State, T, 1, column(T)));
        false ->
            parse_next(Tokens, push(State, T, 1))
    end;
parse_next2([T1 | Tokens], State = #state{stack = [T2 | _]}) when ?CLOSE_BRACKET(T1) ->
    case symmetrical(category(T1)) == category(T2) of
        true ->
            parse_next(Tokens, pop(State));
        false ->
            throw({parse_error, [T1 | Tokens], State, ?LINE})
    end;
parse_next2([T1 = {'||', _} | Tokens], State = #state{stack = [T2 | _]}) when ?IS(T2, '['); ?IS(T2, '<<') ->
    case same_line(T1, Tokens) of
        true ->
            parse_next(Tokens, reindent(State, 1, column(T1) + 2));
        false ->
            parse_next(Tokens, reindent(State, 0))
    end;
parse_next2([{'=', _} | Tokens], State = #state{stack = [T | _]}) when ?OPEN_BRACKET(T) ->
    parse_next(Tokens, State);
parse_next2([T1 = {'=', _} | Tokens], State = #state{stack = [T2 | _]}) when ?IS(T2, '=') ->
    parse_next(Tokens, push(pop(State), T1, 1, column(T1) + 1));
parse_next2([T = {'=', _} | Tokens], State) ->
    parse_next(Tokens, push(State, T, 1, column(T) + 1));
parse_next2(Tokens = [T1 | _], State = #state{stack = [T2 | _]}) when ?IS(T2, '='), not ?IS(T1, ','), not ?IS(T1, ';') ->
    parse_next2(Tokens, pop(State));
parse_next2([{',', _} | Tokens], State = #state{stack = [T | _]}) when ?IS(T, '=') ->
    parse_next(Tokens, pop(State));
parse_next2([{',', _} | Tokens], State) ->
    parse_next(Tokens, State);
parse_next2(Tokens = [{';', _} | _], State = #state{stack = [T | _]}) when ?IS(T, '=') ->
    parse_next2(Tokens, pop(State));
parse_next2([{';', _} | Tokens], State = #state{stack = [T1, T2 | _]}) when ?IS(T1, '->'), ?IS(T2, atom) ->
    parse_function(Tokens, pop(pop(State)));
parse_next2([{';', _} | Tokens], State = #state{stack = [{'->', _}, T | _]}) when ?BRANCH_EXPR(T) ->
    parse_next(Tokens, indent_after(Tokens, pop(State), 2));
parse_next2([{';', _} | Tokens], State) ->
    parse_next(Tokens, State);
parse_next2([{'fun', _}, T | Tokens], State) when not ?IS(T, '(') ->
    parse_next(Tokens, State);
parse_next2([T | Tokens], State) when ?IS(T, 'fun'); ?IS(T, 'receive'); ?IS(T, 'if') ->
    parse_next(Tokens, indent_after(Tokens, push(State, T, 1), 2));
parse_next2([T | Tokens], State) when ?BRANCH_EXPR(T) ->
    parse_next(Tokens, push(State, T, 1));
parse_next2([T | Tokens], State) when ?IS(T, 'of') ->
    parse_next(Tokens, indent_after(Tokens, State, 2));
parse_next2([T1 = {'->', _} | Tokens], State = #state{stack = [T2]}) when ?IS(T2, '-') ->
    parse_next(Tokens, push(State, T1, 0));
parse_next2([T1 = {'->', _} | Tokens], State = #state{stack = [T2]}) when ?IS(T2, atom) ->
    parse_next(Tokens, push(unindent(State), T1, 0));
parse_next2([T1 = {'->', _} | Tokens], State = #state{stack = [T2 | _]}) when ?BRANCH_EXPR(T2) ->
    parse_next(Tokens, push(unindent(State), T1, 1));
parse_next2([{'catch', _} | Tokens], State = #state{stack = [T1, T2 | _]}) when
        not ?IS(T1, 'try'), not (?IS(T1, '->') and ?IS(T2, 'try')) ->
    parse_next(Tokens, State);
parse_next2([T | Tokens], State = #state{stack = [{'try', _} | _]}) when ?IS(T, 'catch') ->
    parse_next(Tokens, indent_after(Tokens, State, 2));
parse_next2([T | Tokens], State = #state{stack = [{'->', _}, {'try', _} | _]}) when ?IS(T, 'catch') ->
    parse_next(Tokens, indent_after(Tokens, pop(State), 2));
parse_next2([T | Tokens], State = #state{stack = [{'try', _} | _]}) when ?IS(T, 'after') ->
    parse_next(Tokens, State);
parse_next2([T | Tokens], State = #state{stack = [{'receive', _} | _]}) when ?IS(T, 'after') ->
    parse_next(Tokens, indent_after(Tokens, unindent(State), 2));
parse_next2([T | Tokens], State = #state{stack = [{'->', _}, {'receive', _} | _]}) when ?IS(T, 'after') ->
    parse_next(Tokens, indent_after(Tokens, pop(State), 2));
parse_next2([T | Tokens], State = #state{stack = [{'->', _} | _]}) when ?IS(T, 'after') ->
    parse_next(Tokens, pop(State));
parse_next2([T | Tokens], State) when ?IS(T, 'begin') ->
    parse_next(Tokens, push(State, T, 1));
parse_next2([{'end', _} | Tokens], State = #state{stack = [T | _]}) when ?IS(T, 'begin'); ?IS(T, 'try') ->
    parse_next(Tokens, pop(State));
parse_next2([{'end', _} | Tokens], State = #state{stack = [{'->', _} | _]}) ->
    parse_next(Tokens, pop(pop(State)));
parse_next2([{dot, _} | Tokens], State = #state{stack = [T]}) when ?IS(T, '-') ->
    parse_next(Tokens, pop(State));
parse_next2([{dot, _} | Tokens], State = #state{stack = [T, _]}) when ?IS(T, '->') ->
    parse_next(Tokens, pop(pop(State)));
parse_next2([], State) ->
    State;
parse_next2(Tokens, State) ->
    throw({parse_error, Tokens, State, ?LINE}).

indent(State, OffTab) ->
    indent(State, OffTab, none).

indent(State, OffTab, Col) ->
    Tabs = State#state.tabs,
    Cols = State#state.cols,
    State#state{tabs = [hd(Tabs) + OffTab | Tabs], cols = [Col | Cols]}.

indent_after([], State, _) ->
    State;
indent_after(_Tokens, State, OffTab) ->
    indent(State, OffTab).

reindent(State, OffTab) ->
    reindent(State, OffTab, none).

reindent(State, OffTab, Col) ->
    [Tab | Tabs] = State#state.tabs,
    [_ | Cols] = State#state.cols,
    State#state{tabs = [Tab + OffTab | Tabs], cols = [Col | Cols]}.

unindent(State = #state{tabs = Tabs, cols = Cols}) ->
    State#state{tabs = tl(Tabs), cols = tl(Cols)}.

push(State, Token, OffTab) ->
    push(State, Token, OffTab, none).

push(State = #state{stack = Stack}, Token, OffTab, Col) ->
    indent(State#state{stack = [Token | Stack]}, OffTab, Col).

pop(State = #state{stack = Stack}) ->
    unindent(State#state{stack = tl(Stack)}).

next_relevant_token(Tokens) ->
    lists:dropwhile(fun(T) -> irrelevant_token(T) end, Tokens).

irrelevant_token(Token) ->
    Chars = ['(', ')', '{', '}', '[', ']', '<<', '>>', '=', '->', '||', ',', ';', dot],
    Keywords = ['fun', 'receive', 'if', 'case', 'try', 'of', 'catch', 'after', 'begin', 'end'],
    Cat = category(Token),
    not lists:member(Cat, Chars ++ Keywords).

same_line(_, []) ->
    false;
same_line(Token, [NextTok | _]) ->
    case line(Token) == line(NextTok) of
        true  -> true;
        false -> false
    end.

symmetrical(')')  -> '(';
symmetrical('}')  -> '{';
symmetrical(']')  -> '[';
symmetrical('>>') -> '<<'.
