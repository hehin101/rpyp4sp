#!/usr/bin/env python3

import subprocess
import sys

if __name__  == '__main__':
    command = ["p4c", sys.argv[1]]
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    _stdout, stderr = process.communicate()
    if "SIGSEGV" in stderr:
        sys.exit(0)
    sys.exit(1)
