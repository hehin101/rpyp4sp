from __future__ import print_function

import os, time

from rpython.rlib.nonconst import NonConstant

from rpyp4sp import p4specast, objects, builtin, context, integers, rpyjson, interp
from rpyp4sp.error import P4Error
from rpyp4sp.test.test_interp import make_context

def command_run_test_jsonl(argv):
    ctx = make_context()
    passed = 0
    skipped = 0
    failed = 0
    error = 0
    with open(argv[2], 'r') as f:
        while 1:
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
                if name not in ctx.glbl.fenv:
                    continue
                func = ctx.glbl.fenv[name]
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
                    print("Function test exception:", name, e.__class__.__name__, e.msg)
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
                    print("Relation test exception:", name, e.__class__.__name__, e.msg)
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
                    print("Builtin test exception:", name, e.__class__.__name__, e.msg)
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
    load_times = []
    run_times = []
    passed = 0
    errors = 0
    for fn in argv[2:]:
        t1 = time.time()
        print(fn)
        with open(fn, 'r') as f:
            content = f.readline()
        assert content is not None
        if not content.startswith("{"):
            continue
        valuejson = rpyjson.loads(content)
        value = objects.BaseV.fromjson(valuejson)
        t2 = time.time()
        print("program loaded in %ss" % (t2 - t1))
        load_times.append(t2 - t1)
        resctx = None
        try:
            resctx, values = interp.invoke_rel(ctx, p4specast.Id("Prog_ok", p4specast.NO_REGION), [value])
        except P4Error as e:
            print("Function test exception:", e, e.msg)
        except KeyError as e:
            print("KeyError")
        t3 = time.time()
        print("executed in %ss" % (t3 - t2))
        run_times.append(t3 - t2)
        if resctx is None:
            errors += 1
            print("relation was not matched, or error")
        else:
            passed += 1
            print("well-typed")
    print("PASSED:", passed)
    print("ERRORS:", errors)
    def fsum(l):
        res = 0.0
        for x in l:
            res += x
        return res
    print("load time; total:", fsum(load_times), "avg:", fsum(load_times) / len(load_times))
    print("run time; total:", fsum(run_times), "avg:", fsum(run_times) / len(run_times))
    print("total time:", fsum(load_times) + fsum(run_times))
    return 0

def main(argv):
    if len(argv) < 3:
        print("usage: %s run-test-jsonl/run-p4-json <fn>" % argv[0])
        return 1
    # load test cases from line-based json file
    # check if file exists
    cmd = argv[1]
    if cmd == 'run-test-jsonl':
        return command_run_test_jsonl(argv)
    if cmd == 'run-p4-json':
        return command_run_p4(argv)
    else:
        print("unknown command", cmd)
        return 2
    return 0

def target(*args):
    return main

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
