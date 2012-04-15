# SublimErl (Erlang Tests)

Overview
--------

SublimErl is a plugin for the text editor [Sublime Text 2](http://www.sublimetext.com/2). It allows you to:

* Run **Eunit** tests (all tests from file / single test)
* Run **Common Tests** ( single file )
* Run **Dialyzer** tests ( single file )

Screenshot
----------

Here's a screenshot of SublimErl running an Eunit specific test in file.

![SublimErl screenshot](http://farm8.staticflickr.com/7065/7081124859_7fd1894549_b.jpg)

Installation
------------
Go to your Sublime Text 2 `Packages` directory

* OS X: `~/Library/Application Support/Sublime Text\ 2/Packages`
* Linux: `~/.Sublime Text 2/Packages/`
* Windows: `%APPDATA%/Sublime Text 2/Packages/`

and clone the repository using the command below:

``` shell
git clone https://ostinelli@github.com/ostinelli/SublimErl.git
```
You may also consider heading to the [downloads](https://github.com/ostinelli/SublimErl/downloads) section and unzipping the downloaded file into the `Packages` directory.

Usage
-----

* Run **single Eunit test**: position your cursor anywhere **within** your test function and hit `Command-Shift-F8`
* Run **all Eunit test** in file: position your cursor **outside** any test function and hit `Command-Shift-F8`
* Run **all Common Tests** in file: view the test file and hit `Command-Shift-F8`
* Run **Dialyzer** on file: view the file and hit `Command-Shift-F9`
* Re-Run the **previous test**: hit `Command-F8` ( you do not need to be viewing the test to launch it )
* View **Common Tests results** in browser: hit `Command-Option-F8` (OSX) | `Command-Alt-F8` (Linux/Win)

A brief introduction video can be seen [[[[HERE]]]]

Dependencies
------------

To use SublimErl, you need to have:

* The editor [Sublime Text 2](http://www.sublimetext.com/2).
* [Erlang](http://www.erlang.org/download.html) (..obviously ^^_).
* Basho's [Rebar](https://github.com/basho/rebar).

To unleash the full power of the plugin, you will also need to comply to:

* OTP standards (i.e. have your project defined according to [OTP Directory Structure](http://www.erlang.org/doc/design_principles/applications.html#id73730)).
* [Rebar's conventions](https://github.com/basho/rebar/wiki/Rebar-and-OTP-conventions).

TL;DR: it basically means to organize your project structure using:

```
--myproject
  |-- ebin
  |-- src
      |-- myproject.app.src
  |-- test
```
