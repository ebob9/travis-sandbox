#!/usr/bin/env python
#
#
# Test some stuff
#
import os

print("Test!")

for key, value in os.environ.items():
    print(f"{key}: {value}")
