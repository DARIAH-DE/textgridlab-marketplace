# About

This is a catalog software for negotiating between an Eclipse-based
program and a wiki-like software that contains additional information
about the plugins to be installed. It is a webservice run as a cgi,
implemented in Python3.

# API

The Eclipse marketplace API is documented at 
https://wiki.eclipse.org/Marketplace/REST

# Adding Plugins to the TextGridLab marketplace

Plugins are located in data.yaml, to add a new plugin you may create a pull request for data.yaml. 
The following template could be used:

```yaml

- !PlugIn
  plugId:
  name:
  category:
  pageId:
  featured:
  installableUnit:
  owner:
  company:
  company_url:
  update_url:
  human_title:
  description: |
    fill a description here
  logo:
  license:
  screenshot:
```

required fields are: name, installableUnit, update_url, human_title, description and license

