import sublime, sublime_plugin
import re

class SublimErlCommand(sublime_plugin.TextCommand):
	def run(self, edit):
		# get current line position
		cursor_position = self.view.sel()[0].a

		# find all regions with a test function definition
		function_regions = self.view.find_all(r"(%.*)?([a-zA-Z0-9_]*_test_\(\)\s*->[^.]*\.)")

		# loop regions
		matching_region = None
		for region in function_regions:
			region_content = self.view.substr(region)
			if not re.match(r"%.*((?:[a-zA-Z0-9_]*)_test_)\(\)\s*->", region_content):
				# function is not commented out
				if region.a <= cursor_position and cursor_position <= region.b:
					matching_region = region
					break

		# get function name
		function_name = None
		if matching_region != None:
			# get function name and arguments
			m = re.match(r"((?:[a-zA-Z0-9_]*)_test_)\(\)\s*->(?:.|\n)", self.view.substr(matching_region))
			if m != None:
				function_name = "%s/0" % m.group(1)

		print function_name
