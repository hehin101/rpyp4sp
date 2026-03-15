import os
import subprocess
import argparse

def decompile_json_to_p4(spectec_path, fuzzer_output_path, fuzzer_p4_path):
    count = 0
    failed_files = []
    for entry in os.scandir(fuzzer_output_path):
        if entry.is_file() and entry.path.endswith(".json"):
            count += 1
            if count % 1000 == 0:
                print(f"decompiling the {count}th file")
            p4_file_path = fuzzer_p4_path + "/" + os.path.basename(entry.path)[:-5] + ".p4"
            command = [spectec_path, "unparse-json-value", "-j", entry.path]
            process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate()
            if stderr:
                failed_files.append((entry.path, stderr))
                continue
            elif stdout.startswith(("Error parsing JSON value:",
                                    "File error:",
                                    "JSON parsing error:",
                                    "Unknown error:")):
                failed_files.append((entry.path, stdout))
                continue
            else:
                with open(p4_file_path, "w") as f:
                    f.write(stdout)
    if failed_files == []:
        print("0 files failed")
    else:
        with open("failed_files.txt", "w") as f:
            for (file, msg) in failed_files:
                f.write(f"file: {file}")
                f.write(f"msg: {msg}\n")
        print(f"{len(failed_files)} files failed, see failed_files.txt")

def move_file(folder, entry, subfolder):
    os.replace(entry.path, folder + subfolder + os.path.basename(entry.path))

def test_p4_compiler_and_spectec(fuzzer_p4_path, compiler_output_path, spectec_path, p4_compiler):
    if not os.path.exists(fuzzer_p4_path + "/rpyp4sp_crash"):
        os.mkdir(fuzzer_p4_path + "/rpyp4sp_crash")
    if not os.path.exists(fuzzer_p4_path + "/p4c_crash"):
        os.mkdir(fuzzer_p4_path + "/p4c_crash")
    if not os.path.exists(fuzzer_p4_path + "/differ"):
        os.mkdir(fuzzer_p4_path + "/differ")
    if not os.path.exists(fuzzer_p4_path + "/welltyped_p4c_ok"):
        os.mkdir(fuzzer_p4_path + "/welltyped_p4c_ok")
    if not os.path.exists(fuzzer_p4_path + "/welltyped_p4c_fail"):
        os.mkdir(fuzzer_p4_path + "/welltyped_p4c_fail")
    if not os.path.exists(fuzzer_p4_path + "/exception_p4c_ok"):
        os.mkdir(fuzzer_p4_path + "/exception_p4c_ok")
    if not os.path.exists(fuzzer_p4_path + "/exception_p4c_fail"):
        os.mkdir(fuzzer_p4_path + "/exception_p4c_fail")

    count = 0
    for entry in os.scandir(fuzzer_p4_path):
        if entry.is_file() and entry.path.endswith(".p4"):
            count += 1
            if count % 1000 == 0:
                print(f"testing the {count}th file")

            if "crash" in entry.path:
                move_file(fuzzer_p4_path, entry, "/rpyp4sp_crash/")
                continue

            spectec_command = [
                spectec_path + "/p4spectec",
                "run-sl",
                "-i",
                spectec_path + "/p4c/p4include",
                "-p",
                entry.path
            ]
            spec_files = [entry.path for entry in os.scandir(spectec_path + "/spec")]
            spec_files.sort()
            spectec_process = subprocess.Popen(spectec_command + spec_files, stdout=subprocess.PIPE,
                                               stderr=subprocess.PIPE, text=True)
            spectec_stdout, _spectec_stderr = spectec_process.communicate()
            is_well_typed = "well-typed" in spectec_stdout

            if is_well_typed == ("exception" in entry.path):
                move_file(fuzzer_p4_path, entry, "/differ/")
                continue

            # print(entry.path)
            p4c_command = [p4_compiler, "--Wdisable", "-o", compiler_output_path, entry.path]
            p4c_process = subprocess.Popen(p4c_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            _p4c_stdout, p4c_stderr = p4c_process.communicate()
            # print(p4c_stderr)

            if "Compiler Bug:" in p4c_stderr:
                move_file(fuzzer_p4_path, entry, "/p4c_crash/")
            elif is_well_typed and not p4c_stderr:
                move_file(fuzzer_p4_path, entry, "/welltyped_p4c_ok/")
            elif is_well_typed and p4c_stderr:
                move_file(fuzzer_p4_path, entry, "/welltyped_p4c_fail/")
            elif not is_well_typed and not p4c_stderr:
                move_file(fuzzer_p4_path, entry, "/exception_p4c_ok/")
            elif not is_well_typed and p4c_stderr:
                move_file(fuzzer_p4_path, entry, "/exception_p4c_fail/")


def test_p4_compiler_only(fuzzer_p4_path, compiler_output_path, p4_compiler):
    if not os.path.exists(fuzzer_p4_path + "/ok"):
        os.mkdir(fuzzer_p4_path + "/ok")
    if not os.path.exists(fuzzer_p4_path + "/not_ok"):
        os.mkdir(fuzzer_p4_path + "/not_ok")

    count = 0
    for entry in os.scandir(fuzzer_p4_path):
        if entry.is_file() and entry.path.endswith(".p4"):
            count += 1
            if count % 1000 == 0:
                print(f"testing the {count}th file")

            # print(entry.path)
            p4c_command = [p4_compiler, "--Wdisable", "-o", compiler_output_path, entry.path]
            p4c_process = subprocess.Popen(p4c_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            _p4c_stdout, p4c_stderr = p4c_process.communicate()
            # print(p4c_stderr)

            if "Compiler Bug:" in p4c_stderr:
                move_file(fuzzer_p4_path, entry, "/not_ok/")
            else:
                move_file(fuzzer_p4_path, entry, "/ok/")


def main(args):
    assert os.path.exists(args.spectec)
    assert os.path.exists(args.fuzzer_output)
    if not os.path.exists(args.fuzzer_p4):
        os.mkdir(args.fuzzer_p4)
    if not os.path.exists(args.p4_compiler_output):
        os.mkdir(args.p4_compiler_output)
    subprocess.check_call(["which", args.p4_compiler])

    if not args.no_decompile:
        print("decompiling json to p4...")
        decompile_json_to_p4(args.spectec + "/p4spectec", args.fuzzer_output, args.fuzzer_p4)
        print("finished decompiling")
    if not args.no_test_compiler:
        print("testing compiler...")
        test_p4_compiler_only(args.fuzzer_p4, args.p4_compiler_output, args.p4_compiler)
        # p4-spectec was too slow for this:
        # test_p4_compiler_only(args.fuzzer_p4, args.p4_compiler_output, args.spectec, args.p4_compiler)
        print("finished testing")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(formatter_class=argparse.ArgumentDefaultsHelpFormatter)
    parser.add_argument("-sp", "--spectec", help="path to p4-spectec",
                        type=str, default="../p4-spectec")
    parser.add_argument("-fo", "--fuzzer-output", help="path to folder with fuzzer output",
                        type=str, default="./fuzz_corpus")
    parser.add_argument("-fp", "--fuzzer-p4", help="path to folder for decompiled p4-programs",
                        type=str, default="./fuzz_p4")
    parser.add_argument("-p4c", "--p4-compiler", help="path to p4-compiler",
                        type=str, default="p4c")
    parser.add_argument("-p4co", "--p4-compiler-output", help="path to folder for compiler output",
                        type=str, default="./p4_compiler_output")
    parser.add_argument("-nd", "--no-decompile", help="script will not decompile files",
                        action="store_true")
    parser.add_argument("-ntc", "--no-test-compiler", help="script will not test compiler",
                        action="store_true")
    args = parser.parse_args()
    main(args)
