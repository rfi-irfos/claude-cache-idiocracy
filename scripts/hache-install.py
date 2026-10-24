#!/usr/bin/env python3
"""Print the safe global Claude settings fragment; installation is explicit."""
import json
from hache_guard.policy import Policy

print(json.dumps({"env": Policy().environment()}, indent=2))
