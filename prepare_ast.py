#!/usr/bin/env pypy
"""
Script to prepare ast.json with AST and file content for P4 error reporting.

This script:
1. Runs p4spectec to generate temp_ast.json
2. Reads all spec/*.watsup files to create file_content dict
3. Combines AST and file content into final ast.json
"""

from __future__ import print_function
import os
import sys
import json
import subprocess
import glob

def main():
    # Change to p4-spectec directory
    p4spectec_dir = 'p4-spectec'
    if not os.path.isdir(p4spectec_dir):
        print("Error: p4-spectec directory not found")
        return 1

    original_dir = os.getcwd()
    os.chdir(p4spectec_dir)

    try:
        if not os.path.isfile("p4-spectec/p4spectec"):
            print("Building p4spectec...")
            result = subprocess.call("make", shell=True)
            if result != 0:
                print("Error: p4spectec could not be successfully built with exit code: %d" % result)
                return 1

        # Step 1: Run p4spectec command to generate temp_ast.json
        print("Running p4spectec to generate AST...")
        cmd = './p4spectec json-ast spec/*.watsup'
        with open('temp_ast.json', 'w') as f:
            result = subprocess.call(cmd, stdout=f, shell=True)

        if result != 0:
            print("Error: p4spectec command failed with exit code %d" % result)
            return 1

        # Step 2: Read all spec/*.watsup files to create file_content lists
        print("Reading spec/*.watsup files...")
        watsup_files = glob.glob('spec/*.watsup')
        filenames = []
        file_contents = []

        for filepath in watsup_files:
            try:
                with open(filepath, 'r') as f:
                    content = f.read()
                # Add to parallel lists
                filenames.append(filepath)
                file_contents.append(content)
                print("Read %s (%d characters)" % (filepath, len(content)))
            except IOError as e:
                print("Warning: Could not read %s: %s" % (filepath, e))

        # Step 3: Parse temp_ast.json
        print("Parsing temp_ast.json...")
        try:
            with open('temp_ast.json', 'r') as f:
                ast_data = json.load(f)
        except (IOError, ValueError) as e:
            print("Error: Could not parse temp_ast.json: %s" % e)
            return 1

        # Step 4: Combine into final structure
        print("Combining AST and file content...")
        spec_dirname = os.path.dirname(os.path.abspath('spec'))
        combined_data = {
            'ast': ast_data,
            'file_content': [filenames, file_contents],
            'spec_dirname': spec_dirname
        }

        # Step 5: Write final ast.json (without extra whitespace)
        output_file = os.path.join(original_dir, 'ast.json')
        print("Writing %s..." % output_file)
        with open(output_file, 'w') as f:
            json.dump(combined_data, f, separators=(',', ':'))

        # Clean up temp file
        if os.path.exists('temp_ast.json'):
            os.remove('temp_ast.json')

        print("Successfully created ast.json with %d files" % len(filenames))
        return 0

    except Exception as e:
        print("Error: %s" % e)
        return 1
    finally:
        os.chdir(original_dir)

if __name__ == '__main__':
    sys.exit(main())
