# -*- encoding: utf-8 -*-
import threading
import sublime, sublime_plugin
import os
import re
import subprocess

from ClassHierarchyManager import ClassHierarchyManager, set_tab_size, NoSymbolException
from helpers import get_symbol, to_underscore
from settings import setting

class_hierarchy_manager = ClassHierarchyManager()
set_tab_size(setting('tab_size'))

is_hierarchy_ctags_in_building = False

is_hierarchy_tree_in_loading = False
is_hierarchy_tree_loaded = False

def check_if_thread_finished(thread, did_finished):
    if thread.is_alive():
        sublime.set_timeout(lambda: check_if_thread_finished(thread, did_finished), 500)
    else:
        did_finished()

class RebuildHierarchyCtagsThread(threading.Thread):
    def __init__(self, ctags_command, ctags_file, project_dir):
        threading.Thread.__init__(self)
        self.ctags_command = ctags_command
        self.ctags_file = ctags_file
        self.project_dir = project_dir

    def run(self):
        global is_hierarchy_ctags_in_building

        ctags_command = self.ctags_command

        # Replace -f arg with the path from setting
        ctags_command = re.sub(" -f *[^ ]+", "", ctags_command)
        ctags_command += " -f %s" % self.ctags_file

        p = subprocess.Popen(ctags_command, cwd=self.project_dir, shell=1, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        p.wait()

        is_hierarchy_ctags_in_building = False

class RebuildHierarchyCtags(sublime_plugin.TextCommand):
    def run(self, edit):
        global is_hierarchy_ctags_in_building

        if is_hierarchy_ctags_in_building:
            sublime.status_message("Now re/building hierarchy ctags... Please be patient.")
            return

        is_hierarchy_ctags_in_building = True
        sublime.status_message("Re/Building hierarchy ctags... Please be patient.")
        thread = RebuildHierarchyCtagsThread(setting('ctags_command'), setting('ctags_file'), self.view.window().folders()[0])

        did_finished = lambda: self.view.run_command('reload_hierarchy_tree')

        thread.start()
        sublime.set_timeout(lambda: check_if_thread_finished(thread, did_finished), 500)

class ReloadHierarchyTreeThread(threading.Thread):
    def __init__(self, ctags_file_path):
        threading.Thread.__init__(self)
        self.ctags_file_path = ctags_file_path

    def run(self):
        global is_hierarchy_tree_in_loading, is_hierarchy_tree_loaded

        class_hierarchy_manager.parse_tags_file(self.ctags_file_path)
        is_hierarchy_tree_loaded = True
        is_hierarchy_tree_in_loading = False

class ReloadHierarchyTree(sublime_plugin.TextCommand):
    def run(self, edit, caller=None):
        global is_hierarchy_tree_in_loading, is_hierarchy_tree_loaded

        if is_hierarchy_tree_in_loading:
            sublime.status_message("Now re/loading hierarchy tree... Please be patient.")
            return

        is_hierarchy_tree_in_loading = True
        is_hierarchy_tree_loaded = False
        sublime.status_message("Re/Loading hierarchy tree... Please be patient.")
        thread = ReloadHierarchyTreeThread('/Users/junhyunje/Studies/class-hierarchy/tags-hierarchy') # FIXME

        if caller:
            did_finished = lambda: self.view.run_command(to_underscore(caller))
        else:
            did_finished = lambda: sublime.status_message("Re/Loading hierarchy tree is finished!")

        thread.start()
        sublime.set_timeout(lambda: check_if_thread_finished(thread, did_finished), 500)

class ShowHierarchyBase(sublime_plugin.TextCommand):
    @get_symbol
    def run(self, edit, view, symbol):
        global is_hierarchy_tree_loaded

        if is_hierarchy_tree_loaded:
            if symbol:
                try:
                    self.hierarchy_function(symbol)
                except NoSymbolException:
                    sublime.status_message("Can't find \"%s\"." % symbol)
            else:
                print "Symbol None" # FIXME
        else:
            view.run_command('reload_hierarchy_tree', {'caller': self.__class__.__name__})

class ShowUpwardHierarchy(ShowHierarchyBase):
    def __init__(self, args):
        sublime_plugin.TextCommand.__init__(self, args)
        self.hierarchy_function = class_hierarchy_manager.show_upward_hierarchy

class ShowDownwardHierarchy(ShowHierarchyBase):
    def __init__(self, args):
        sublime_plugin.TextCommand.__init__(self, args)
        self.hierarchy_function = class_hierarchy_manager.show_downward_hierarchy
