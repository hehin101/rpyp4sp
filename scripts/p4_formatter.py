import os
import subprocess
import argparse

def main(args):
    assert os.path.exists(args.spectec)
    for file in args.files:
        compile_command = [args.spectec, "p4-program-value-json", "-p", file]
        process = subprocess.Popen(compile_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        if stderr:
            print(f"failed to compile '{file}'")
            print(stdout)
            print(stderr)
            continue
        tmp_file = file + ".tmp"
        with open(tmp_file, "w") as f:
            f.write(stdout)

        decompile_command = [args.spectec, "unparse-json-value", "-j", tmp_file]
        process = subprocess.Popen(decompile_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        stdout, stderr = process.communicate()
        os.remove(tmp_file)
        if stderr:
            print(f"failed to decompile '{file}'")
            print(stdout)
            print(stderr)
            continue
        with open(file, "w") as f:
            f.write(stdout)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-sp", "--spectec", help="path to p4-spectec",
                        type=str, default="../p4-spectec/p4spectec")
    parser.add_argument("files", help="all files that should be formatted",
                        type=str, nargs='+')
    args = parser.parse_args()
    main(args)
