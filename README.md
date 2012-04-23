# SublimErl (Erlang Tests & Code Completion)

Overview
--------

SublimErl is a plugin for the text editor [Sublime Text 2](http://www.sublimetext.com/2). It allows you to:

* Benefit from **Code Completion** ( all Erlang libs + your current project )
* Run **Eunit** tests ( all tests from file / single test )
* Run **Common Tests** ( single file )
* Run **Dialyzer** tests ( single file )

All within your test editor.

Screenshots
-----------

Here's a screenshot of SublimErl's **Code Completion** feature:

![SublimErl screenshot](http://www.ostinelli.net/_out_images/code_completion.gif)

Here's a screenshot of SublimErl **running an Eunit specific test** in file.

![SublimErl screenshot](http://www.ostinelli.net/_out_images/running_test.jpeg)

Installation
------------
SublimErl currently supports only on **OSX** and **Linux**. There are 3 ways to install it.

##### 1. Sublime Package Control
Download and install the [Sublime Package Control](http://wbond.net/sublime_packages/package_control). This package controller allows you to easily manage your Sublime Text 2 plugins (installs / removals / upgrades).

##### 2. Git Clone
Go to your Sublime Text 2 `Packages` directory:

* OS X: `~/Library/Application Support/Sublime Text\ 2/Packages`
* Linux: `~/.Sublime Text 2/Packages/`

and clone the repository using the command below:

``` shell
git clone https://github.com/ostinelli/SublimErl.git
```

##### 3. File Download
Head to the [downloads](https://github.com/ostinelli/SublimErl/downloads) section and unzipping the downloaded file into the Sublime Text 2 `Packages` directory.

Usage
-----

* **Code Completion**: Just type and select available options
* Run **single Eunit test**: position your cursor anywhere **within** your test function and hit `Command-Shift-F8`
* Run **all Eunit test** in file: position your cursor **outside** any test function and hit `Command-Shift-F8`
* Run **all Common Tests** in file: view the test file and hit `Command-Shift-F8`
* Run **Dialyzer** on file: view the file and hit `Command-Shift-F9`
* Re-Run the **previous test**: hit `Command-F8` ( you do not need to be viewing the test to launch it )
* View **Common Tests results** in browser: hit `Command-Option-F8` (OSX) | `Command-Alt-F8` (Linux/Win)

A brief introduction video can be seen [here](http://www.youtube.com/watch?v=T0rD0CQM4Yg):

[![SublimErl screenshot](http://farm8.staticflickr.com/7263/6935974110_c07c6a6afe_b.jpg)](http://www.youtube.com/watch?v=T0rD0CQM4Yg)

Dependencies
------------

To use SublimErl, you need to have:

* The editor [Sublime Text 2](http://www.sublimetext.com/2).
* [Erlang](http://www.erlang.org/download.html) ( ..obviously ^^_ ).
* Basho's [Rebar](https://github.com/basho/rebar).

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
```