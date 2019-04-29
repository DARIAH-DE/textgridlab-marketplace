# About

This is a catalog software for negotiating between an Eclipse-based
program and a wiki-like software that contains additional information
about the plugins to be installed. 

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

# Develop and Test
The new version of the marketplace uses flask and gunicorn and will not be running as cgi anymore.

Install dependencies

        apt install flask gunicorn3 python3-pytest python3-pytest-flask python3-lxml python3-yaml

Run locally (for development)

        python3 marketplace.py

Then point your browser to localhost:5000, e.g: <http://localhost:5000/featured/api/p>

Pytest: in root dir run:

        PYTHONPATH=. pytest-3

# Install for production (not yet tested)

Deployment for production should be done with gunicorn and nginx, a good resource seems to be

* https://philchen.com/2019/02/11/how-to-make-a-python-web-app-in-virtualenv-using-flask-gunicorn-nginx-on-ubuntu-18-04

using a virtual env should not be necessary though, as dependencies are moderate and available with apt-get



