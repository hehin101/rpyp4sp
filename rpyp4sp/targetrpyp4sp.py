from __future__ import print_function

import os

from rpython.rlib.nonconst import NonConstant

from rpyp4sp import p4specast, objects, builtin, context, integers, rpyjson, interp
from rpyp4sp.error import P4Error
from rpyp4sp.test.test_interp import make_context

def main(argv):
    if not len(argv) == 2:
        print("usage: %s <fn.jsonl>" % argv[0])
        return 1
    # load test cases from line-based json file
    # check if file exists
    ctx = make_context()
    passed = 0
    failed = 0
    error = 0
    with open(argv[1], 'r') as f:
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
                        failed += 1
                        print("Function test failed:", name, value, res_value)
                    else:
                        passed += 1
                        print("Function test passed:", name)
                except P4Error as e:
                    #import pdb; pdb.xpm()
                    error += 1
                    print("Function test exception:", name, e)
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
                                failed += 1
                                print("Relation test failed:", name, resval, resval_exp)
                            else:
                                passed += 1
                                print("Relation test passed:", name)
                except P4Error as e:
                    #import pdb; pdb.xpm()
                    error += 1
                    print("Relation test exception:", name, e)
                    continue
                except KeyError as e:
                    #import pdb; pdb.xpm()
                    error += 1
                    print("Relation test exception:", name, e)
                    continue
            else:
                assert 0
    print("PASSED:", passed)
    print("FAILED", failed)
    print("ERROR ", error)
    return 0

def target(*args):
    return main

if __name__ == '__main__':
    import sys
    sys.exit(main(sys.argv))
