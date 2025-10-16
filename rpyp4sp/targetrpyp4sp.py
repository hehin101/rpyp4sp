from __future__ import print_function

import os, time

from rpython.rlib.nonconst import NonConstant
from rpython.rlib import objectmodel, jit, rsignal

from rpyp4sp import p4specast, objects, builtin, context, integers, rpyjson, interp
from rpyp4sp.error import P4Error, format_p4error
from rpyp4sp.test.test_interp import make_context

@objectmodel.specialize.arg(4)
def parse_args(argv, shortname, longname="", want_arg=True, many=False):
    # crappy argument handling
    reslist = []
    if many:
        assert want_arg
    i = 0
    while i < len(argv):
        if argv[i] == shortname or argv[i] == longname:
            if not want_arg:
                res = argv[i]
                del argv[i]
                return res
            if len(argv) == i + 1:
                print("missing argument after " + argv[i])
                raise ValueError
            arg = argv[i + 1]
            del argv[i : i + 2]
            if many:
                reslist.append(arg)
            else:
                return arg
            continue
        i += 1
    if many:
        return reslist


def parse_flag(argv, flagname, longname=""):
    return bool(parse_args(argv, flagname, longname=longname, want_arg=False))

def command_run_test_jsonl(argv):
    ctx = make_context()
    passed = 0
    skipped = 0
    failed = 0
    error = 0
    with open(argv[1], 'r') as f:
        while 1:
            p = rsignal.pypysig_getaddr_occurred()
            if p.c_value < 0:
                # ctrl-c was pressed
                os.write(2, "ctrl-c pressed\n")
                return -2
            if NonConstant(False):
                f.read(10021)
            line = f.readline()
            if not line:
                break
            if not line.startswith('{'):
                continue
            callspec = rpyjson.loads(line)
            what = callspec.get_dict_value('calltype').value_string()
            args = callspec.get_dict_value('inputs')
            input_values = [objects.BaseV.fromjson(arg) for arg in args]
            if what == 'function':
                res_value = objects.BaseV.fromjson(callspec.get_dict_value('result'))
                name = callspec.get_dict_value('name').value_string()
                if name not in ctx.venv_keys.glbl.fenv:
                    continue
                func = ctx.venv_keys.glbl.fenv[name]
                try:
                    _, value = interp.invoke_func_def_attempt_clauses(ctx, func, input_values)
                    if not value.eq(res_value):
                        if "FRESH" in value.tostring():
                            skipped += 1
                            print("Function test skipped due to FRESH:", name)
                        else:
                            failed += 1
                            print("Function test failed:", name, value.tostring(), res_value.tostring())
                    else:
                        passed += 1
                        print("Function test passed:", name)
                except P4Error as e:
                    #import pdb; pdb.xpm()
                    error += 1
                    print("Function test exception:", name)
                    print(format_p4error(e, ctx.venv_keys.glbl.file_content))
                    continue
                except KeyError as e:
                    #import pdb; pdb.xpm()
                    error += 1
                    print("Function test exception:", name, e)
                    continue
            elif what == 'relation':
                res_values = [objects.BaseV.fromjson(rv) for rv in callspec.get_dict_value('results')]
                name = callspec.get_dict_value('name').value_string()
                try:
                    _, values = interp.invoke_rel(ctx, p4specast.Id(name, p4specast.NO_REGION), input_values)
                    if values is None or len(values) != len(res_values):
                        failed += 1
                        print("Relation test wrong number of results", name)
                    else:
                        for i, resval in enumerate(values):
                            resval_exp = res_values[i]
                            if not resval.eq(resval_exp):
                                if "FRESH" in resval_exp.tostring():
                                    skipped += 1
                                    print("Relation test skipped due to FRESH:", name)
                                else:
                                    failed += 1
                                    print("Relation test failed:", name, resval.tostring(), resval_exp.tostring())
                                break
                        else:
                            passed += 1
                            print("Relation test passed:", name)
                except P4Error as e:
                    #import pdb; pdb.xpm()
                    error += 1
                    print("Relation test exception:", name)
                    print(format_p4error(e, ctx.venv_keys.glbl.file_content))
                    continue
                except KeyError as e:
                    #import pdb; pdb.xpm()
                    error += 1
                    print("Relation test exception:", name, e)
                    continue
            elif what == 'builtin':
                name = callspec.get_dict_value('name').value_string()
                try:
                    res_value = objects.BaseV.fromjson(callspec.get_dict_value('result'))
                    targs = callspec.get_dict_value('targs').value_array()
                    targs = [p4specast.Type.fromjson(t) for t in targs]
                    value = builtin.invoke(ctx, p4specast.Id(name, p4specast.NO_REGION), targs, input_values)
                    if not value.eq(res_value):
                        failed += 1
                        print("Builtin test failed:", name, value, res_value)
                    else:
                        passed += 1
                        print("Builtin test passed:", name)
                except P4Error as e:
                    #import pdb; pdb.xpm()
                    error += 1
                    print("Builtin test exception:", name)
                    print(format_p4error(e, ctx.venv_keys.glbl.file_content))
                    continue
                except KeyError as e:
                    #import pdb; pdb.xpm()
                    error += 1
                    print("Builtin test exception:", name, e)
                    continue
            else:
                assert 0
    print("PASSED:", passed)
    print("SKIPPED:", skipped)
    print("FAILED", failed)
    print("ERROR ", error)
    return 0

def command_run_p4(argv):
    ctx = make_context()
    print_times = not parse_flag(argv, "--no-times")
    load_times = []
    run_times = []
    passed = 0
    errors = 0
    for fn in argv[1:]:
        t1 = time.time()
        print(fn)
        stat = os.stat(fn)
        with open(fn, 'r') as f:
            content = f.read(stat.st_size)
        assert content is not None
        if not content.startswith("{"):
            continue
        valuejson = rpyjson.loads(content)
        value = objects.BaseV.fromjson(valuejson)
        t2 = time.time()
        if print_times:
            print("program loaded in %ss" % (t2 - t1))
        load_times.append(t2 - t1)
        resctx = None
        try:
            resctx, values = interp.invoke_rel(ctx, p4specast.Id("Program_ok", p4specast.NO_REGION), [value])
        except P4Error as e:
            print("P4 execution exception:")
            print(format_p4error(e, ctx.venv_keys.glbl.file_content, spec_dirname=ctx.venv_keys.glbl.spec_dirname))
        except KeyError as e:
            print("KeyError")
        t3 = time.time()
        if print_times:
            print("executed in %ss" % (t3 - t2))
        run_times.append(t3 - t2)
        if resctx is None:
            errors += 1
        else:
            passed += 1
            print("well-typed")
        p = rsignal.pypysig_getaddr_occurred()
        if p.c_value < 0:
            # ctrl-c was pressed
            os.write(2, "ctrl-c pressed\n")
            return 1
    print("PASSED:", passed)
    print("ERRORS:", errors)
    def fsum(l):
        res = 0.0
        for x in l:
            res += x
        return res
    if print_times:
        print("load time; total:", fsum(load_times), "avg:", fsum(load_times) / len(load_times))
    if print_times:
        print("run time; total:", fsum(run_times), "avg:", fsum(run_times) / len(run_times))
    if print_times:
        print("total time:", fsum(load_times) + fsum(run_times))
    return 0

def print_csv_line(*args):
    print(convert_csv_line(*args))

def convert_csv_line(*args):
    if len(args) == 0:
        assert 0
    if len(args) == 1:
        return str(args[0])
    return "%s, %s" % (args[0], convert_csv_line(*args[1:]))

def command_bench_p4(argv):
    reps = parse_args(argv, "-n", "--repetitions")
    if reps:
        reps = int(reps)
    else:
        reps = 5
    comment = parse_args(argv, "-c", "--comment")
    if not comment:
        comment = ''
    t1 = time.time()
    ctx = make_context()
    t2 = time.time()
    fns = argv[1:]
    if not fns:
        print("usage: %s bench-p4-json [-n/--repetitions N] [-c/--comment COMMENT] fn1, fn2, fn3, ...")
        return -1
    print_csv_line("filename", "action", "iteration", "time", "outcome", "comment", "epoch", "executable")
    print_csv_line("ast.json", "load", "0", str(t2 - t1), "ok", comment, str(t2), argv[0])
    for fn in fns:
        p = rsignal.pypysig_getaddr_occurred()
        if p.c_value < 0:
            # ctrl-c was pressed
            os.write(2, "ctrl-c pressed\n")
            return 1
        t1 = time.time()
        stat = os.stat(fn)
        with open(fn, 'r') as f:
            content = f.read(stat.st_size)
        assert content is not None
        if not content.startswith("{"):
            continue
        valuejson = rpyjson.loads(content)
        value = objects.BaseV.fromjson(valuejson)
        t2 = time.time()
        print_csv_line(fn, "load", "0", str(t2 - t1), "ok", comment, str(t2), argv[0])
        for i in range(reps):
            t1 = time.time()
            resctx = None
            res = None
            try:
                resctx, values = interp.invoke_rel(ctx, p4specast.Id("Program_ok", p4specast.NO_REGION), [value])
            except P4Error as e:
                res = "exception"
            except KeyError as e:
                res = "keyerror"
            t2 = time.time()
            if resctx is None:
                if res is None:
                    res = "failed"
            else:
                res = "passed"
            print_csv_line(fn, "run", str(i), str(t2 - t1), res, comment, str(t2), argv[0])
    return 0

JIT_HELP = ["Advanced JIT options:", '', '']
JIT_HELP.extend([" %s=<value>\n     %s (default: %s)\n" % (
    key, jit.PARAMETER_DOCS[key], value)
    for key, value in jit.PARAMETERS.items()]
)
JIT_HELP.extend([" off", "    turn JIT off", "", " help", "    print this page"])
JIT_HELP = "\n".join(JIT_HELP)

def print_help_jit():
    print(JIT_HELP)

def main(argv):
    jitopts = parse_args(argv, "--jit")
    if jitopts:
        if jitopts == "help":
            print_help_jit()
            return 0
        try:
            jit.set_user_param(None, jitopts)
        except ValueError:
            print("invalid jit option")
            return 1
    if len(argv) < 3:
        print("usage: %s run-test-jsonl/run-p4-json/bench-p4-json <fns>" % argv[0])
        return 1
    if objectmodel.we_are_translated():
        rsignal.pypysig_setflag(rsignal.SIGINT)

    # load test cases from line-based json file
    # check if file exists
    cmd = argv[1]
    del argv[1]
    if cmd == 'run-test-jsonl':
        return command_run_test_jsonl(argv)
    if cmd == 'run-p4-json':
        return command_run_p4(argv)
    if cmd == 'bench-p4-json':
        return command_bench_p4(argv)
    else:
        print("unknown command", cmd)
        return 2
    return 0

def target(*args):
    return main

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
