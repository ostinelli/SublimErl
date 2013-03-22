# SublimErl (Erlang Tests & Code Completion)

Overview
--------

SublimErl is a plugin for the text editor [Sublime Text 2](http://www.sublimetext.com/2). It allows you to:

* Benefit from **Code Completion** ( all Erlang libs + your current project )
* Allows you to **Auto-Indent**  your Erlang code
* Run **Eunit** tests ( all tests for module / single test )
* Run **Common Tests** ( all tests for module )
* Run **Dialyzer** tests ( single module )
* **Goto any exported function** of your project easily
* Access **man pages** from the text editor

All within your test editor.

A brief feature introduction video can be seen [here](http://www.youtube.com/watch?v=KIzxbjlHmu0):

[![SublimErl screenshot](http://www.ostinelli.net/_out_images/video.png)](http://www.youtube.com/watch?v=KIzxbjlHmu0)

Screenshots
-----------

Here's a screenshot of SublimErl's **Code Completion** feature:

![SublimErl screenshot](http://www.ostinelli.net/_out_images/code_completion_full.gif)

Here's a screenshot of SublimErl's **Auto-Indenting** feature:

![SublimErl screenshot](http://www.ostinelli.net/_out_images/indenting.gif)

Here's a screenshot of SublimErl **running an Eunit specific test** in file.

![SublimErl screenshot](http://www.ostinelli.net/_out_images/running_test.jpeg)

Usage
-----

* **Code Completion**: Just type and select available options
* **Auto-Indenting**: hit `Command-Option-L` to auto-intent an entire file
* Run **single Eunit**: position your cursor anywhere **within** your test function and hit `Command-Shift-F8`
* Run **all Eunit tests** in file: position your cursor **outside** any test function and hit `Command-Shift-F8`
* Run **all CT tests** in file: view the file and hit `Command-Shift-F8`
* Run **Dialyzer** on file: view the file and hit `Command-Shift-F9`
* Re-Run the **previous test**: hit `Command-F8` ( you do not need to be viewing the test to launch it )
* View **Common Tests results** in browser: hit `Command-Option-F8` (OSX) | `Command-Alt-F8` (Linux/Win)
* **Goto any exported function** of your project easily: hit `Command-Option-p` (OSX) | `Command-Alt-p` (Linux/Win) and select a function
* To access **man pages**: hit `Command-Option-i` (OSX) | `Command-Alt-i` (Linux/Win) and select a module

Installation
------------
SublimErl currently supports only on **OSX** and **Linux**. There are 3 ways to install it.

##### 1. Sublime Package Control
Download and install the [Sublime Package Control](http://wbond.net/sublime_packages/package_control). This package controller allows you to easily manage your Sublime Text 2 plugins (installs / removals / upgrades).

SublimErl's latest stable versions are pushed automatically to the package control. However, if you want the latest and greatest, you'll have to use one of the other following options.

##### 2. Git Clone
Go to your Sublime Text 2 `Packages` directory:

* OS X: `~/Library/Application Support/Sublime Text 2/Packages`
* Linux: `~/.Sublime Text 2/Packages/`

and clone the repository using the command below:

``` shell
git clone https://github.com/ostinelli/SublimErl.git
```

##### 3. File Download
Head to the [downloads](https://github.com/ostinelli/SublimErl/downloads) section and unzipping the downloaded file into the Sublime Text 2 `Packages` directory.

Configuration
-------------

SublimErl needs and will try to detect the paths of the following executables: **rebar**, **erl**, **escript** and **dialyzer**. If it doesn't succeed to find those, or if you prefer to manually configure these path, you can set them in the `SublimErl.sublime-settings` file, located in the `SublimErl` plugin directory.

Dependencies
------------

To use SublimErl, you need to have:

* The editor [Sublime Text 2](http://www.sublimetext.com/2).
* [Erlang](http://www.erlang.org/download.html) ( ..obviously ^^_ ).
* Basho's [Rebar](https://github.com/basho/rebar) built after September 13th, 2012 (which has support for the `tests=` option).
* (optional) [Erlang man pages](http://www.erlang.org/download.html) if you use this functionality.

To unleash the full power of the plugin, you will also need to comply to:

* OTP standards ( i.e. have your project defined according to [OTP Directory Structure](http://www.erlang.org/doc/design_principles/applications.html#id73730) ).
* [Rebar's conventions](https://github.com/basho/rebar/wiki/Rebar-and-OTP-conventions).

TL;DR: it basically means to organize your project structure using:

```
-- myproject
   |-- ebin
   |-- src
       |-- myproject.app.src
   |-- test
   |-- ...
```

or, for example, a more complex project structure defined in rebar.conf:

```
-- myproject
   rebar.config
   |-- apps
       |-- app1
       |-- app2
   |-- deps
       |-- dep1
       |-- dep2
   |-- ...
```

Known issues
------------

We have had reports that some plugin functionalities experience unwanted behaviour (freezing) with the Erlang precompiled package provided by Erlang Solutions, see [issue #56](https://github.com/ostinelli/SublimErl/issues/56). We're looking into this.
