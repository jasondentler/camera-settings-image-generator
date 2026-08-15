# Copyright 2026 Jason Dentler
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0

import os
import tomllib  # Built-in for Python 3.11+

DEFAULT_APP_NAME = "Camera Settings Image Generator"
DEFAULT_APP_VERSION = "0.1.0"


def get_project_metadata():
    """Reads app name and version from pyproject.toml."""
    toml_path = os.path.join(os.path.dirname(__file__), "..", "pyproject.toml")
    try:
        with open(toml_path, "rb") as f:
            data = tomllib.load(f)
            project = data.get("project", {})
            name = project.get("name", DEFAULT_APP_NAME)
            version = project.get("version", DEFAULT_APP_VERSION)
            return name, version
    except Exception:
        return DEFAULT_APP_NAME, DEFAULT_APP_VERSION


APP_NAME, APP_VERSION = get_project_metadata()
APP_STRING = f"{APP_NAME} v{APP_VERSION}"
