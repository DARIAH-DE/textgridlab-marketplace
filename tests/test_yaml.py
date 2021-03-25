from app.main import load_data

from pprint import pprint

def test_yaml_parseable():
  load_data()

def test_unique_plugin_ids():
  plugins = load_data()
  ids_found = set()
  for plugin in plugins:
    assert(not plugin.plugId in ids_found)
    ids_found.add(plugin.plugId)


