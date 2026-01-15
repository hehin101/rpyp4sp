#!/usr/bin/env python3

import subprocess
import sys
import os

if __name__  == '__main__':
    # run p4c
    p4c_command = ["p4c", sys.argv[1]]
    p4c_process = subprocess.Popen(p4c_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    p4c_stdout, p4c_stderr = p4c_process.communicate()
    if "SIGSEGV" not in p4c_stderr:
        sys.exit(1)

    # run p4-spectec
    spectec_path = "<absolute spectec path>"
    spectec_command = [
        spectec_path + "/p4spectec",
        "run-sl",
        "-i",
        spectec_path + "/p4c/p4include",
        "-p",
        sys.argv[1]
    ]
    spec_files = [entry.path for entry in os.scandir(spectec_path + "/spec")]
    spec_files.sort()
    spectec_process = subprocess.Popen(spectec_command + spec_files, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    spectec_stdout, spectec_stderr = spectec_process.communicate()
    if "well-typed" not in spectec_stdout:
        sys.exit(1)

    sys.exit(0)
