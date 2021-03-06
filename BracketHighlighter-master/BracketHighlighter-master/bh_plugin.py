import sublime
import sublime_plugin
from os.path import normpath, join
import imp
from collections import namedtuple
import sys
import traceback
import re
from BracketHighlighter.bh_logging import log


class Payload(object):
    status = False
    plugin = None
    args = None

    @classmethod
    def clear(cls):
        cls.status = False
        cls.plugin = None
        cls.args = None


class BracketRegion (namedtuple('BracketRegion', ['begin', 'end'], verbose=False)):
    """
    Bracket Regions for plugins
    """

    def move(self, begin, end):
        """
        Move bracket region to different points
        """

        return self._replace(begin=begin, end=end)

    def size(self):
        """
        Get the size of the region
        """

        return abs(self.begin - self.end)

    def toregion(self):
        """
        Convert to sublime region
        """

        return sublime.Region(self.begin, self.end)


def is_bracket_region(obj):
    """
    Check if object is a BracketRegion
    """

    return isinstance(obj, BracketRegion)


def sublime_format_path(pth):
    m = re.match(r"^([A-Za-z]{1}):(?:/|\\)(.*)", pth)
    if sublime.platform() == "windows" and m is not None:
        pth = m.group(1) + "/" + m.group(2)
    return pth.replace("\\", "/")


def load_modules(obj, loaded):
    """
    Load bracket plugin modules
    """

    plib = obj.get("plugin_library")
    if plib is None:
        return

    try:
        module = ImportModule.import_module(plib, loaded)
        obj["compare"] = getattr(module, "compare", None)
        obj["post_match"] = getattr(module, "post_match", None)
        obj["validate"] = getattr(module, "validate", None)
        loaded.add(plib)
    except:
        log("Could not load module %s\n%s" % (plib, str(traceback.format_exc())))
        raise


class ImportModule(object):
    @classmethod
    def import_module(cls, module_name, loaded=None):
        # Pull in built-in and custom plugin directory
        if module_name.startswith("bh_modules."):
            path_name = join("Packages", "BracketHighlighter", normpath(module_name.replace('.', '/')))
        else:
            path_name = join("Packages", normpath(module_name.replace('.', '/')))
        path_name += ".py"
        if loaded is not None and module_name in loaded:
            module = sys.modules[module_name]
        else:
            module = imp.new_module(module_name)
            sys.modules[module_name] = module
            exec(compile(sublime.load_resource(sublime_format_path(path_name)), module_name, 'exec'), sys.modules[module_name].__dict__)
        return module

    @classmethod
    def import_from(cls, module_name, attribute):
        return getattr(cls.import_module(module_name), attribute)


class BracketPluginRunCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        try:
            Payload.args["edit"] = edit
            Payload.plugin.run(**Payload.args)
            Payload.status = True
        except Exception:
            print("BracketHighlighter: Plugin Run Error:\n%s" % str(traceback.format_exc()))


class BracketPlugin(object):
    """
    Class for preparing and running plugins
    """

    def __init__(self, plugin, loaded):
        """
        Load plugin module
        """

        self.enabled = False
        self.args = plugin['args'] if ("args" in plugin) else {}
        self.plugin = None
        if 'command' in plugin:
            plib = plugin['command']
            try:
                module = ImportModule.import_module(plib, loaded)
                self.plugin = getattr(module, 'plugin')()
                loaded.add(plib)
                self.enabled = True
            except Exception:
                print('BracketHighlighter: Load Plugin Error: %s\n%s' % (plugin['command'], traceback.format_exc()))

    def is_enabled(self):
        """
        Check if plugin is enabled
        """

        return self.enabled

    def run_command(self, view, name, left, right, selection):
        """
        Load arguments into plugin and run
        """

        Payload.status = False
        Payload.plugin = self.plugin()
        setattr(Payload.plugin, "left", left)
        setattr(Payload.plugin, "right", right)
        setattr(Payload.plugin, "view", view)
        setattr(Payload.plugin, "selection", selection)
        setattr(Payload.plugin, "nobracket", False)
        self.args["edit"] = None
        self.args["name"] = name
        Payload.args = self.args

        # Call a TextCommand to run the plugin so it can feed in the Edit object
        view.run_command("bracket_plugin_run")

        if Payload.status:
            left, right, selection, nobracket = Payload.plugin.left, Payload.plugin.right, Payload.plugin.selection, Payload.plugin.nobracket
        Payload.clear()

        return left, right, selection, nobracket


class BracketPluginCommand(object):
    """
    Bracket Plugin base class
    """

    def run(self, bracket, content, selection):
        """
        Runs the plugin class
        """

        pass
