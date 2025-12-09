import os
import subprocess
import argparse

def decompile_json_to_p4(spectec_path, fuzzer_output_path, fuzzer_p4_path):
    for entry in os.scandir(fuzzer_output_path):
        if entry.is_file() and entry.path.endswith(".json"):
            p4_file_path = fuzzer_p4_path + "/" + os.path.basename(entry.path)[:-5] + ".p4"
            command = [spectec_path, "unparse-json-value", "-j", entry.path]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            if stderr:
                print(stderr)
                break
            else:
                with open(p4_file_path, "w") as f:
                    f.write(stdout)

def test_p4_compiler(fuzzer_p4_path, compiler_output_path, p4_compiler):
    for entry in os.scandir(fuzzer_p4_path):
        if entry.is_file() and entry.path.endswith(".p4"):
            command = [p4_compiler, "--Wdisable", "-o", compiler_output_path, entry.path]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            _stdout, stderr = process.communicate()
            if stderr:
                print(stderr)
                break

def main(args):
    assert os.path.exists(args.spectec)
    assert os.path.exists(args.fuzzer_output)
    if not os.path.exists(args.fuzzer_p4):
        os.mkdir(args.fuzzer_p4)
    if not os.path.exists(args.p4_compiler_output):
        os.mkdir(args.p4_compiler_output)
    subprocess.check_call(["which", args.p4_compiler])

    print("decompiling json to p4...")
    decompile_json_to_p4(args.spectec, args.fuzzer_output, args.fuzzer_p4)
    print("finished decompiling")
    print("testing compiler...")
    test_p4_compiler(args.fuzzer_p4, args.p4_compiler_output, args.p4_compiler)
    print("finished testing")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-sp", "--spectec", help="path to p4-spectec",
                        type=str, default="../p4-spectec/p4spectec")
    parser.add_argument("-fo", "--fuzzer-output", help="path to folder with fuzzer output",
                        type=str, default="./fuzz_corpus")
    parser.add_argument("-fp", "--fuzzer-p4", help="path to folder for decompiled p4-programs",
                        type=str, default="./fuzz_p4")
    parser.add_argument("-p4c", "--p4-compiler", help="path to p4-compiler",
                        type=str, default="p4c")
    parser.add_argument("-p4co", "--p4-compiler-output", help="path to folder for compiler output",
                        type=str, default="./p4_compiler_output")
    args = parser.parse_args()
    main(args)
