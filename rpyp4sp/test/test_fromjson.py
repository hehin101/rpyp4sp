from __future__ import print_function
import os
from rpyp4sp import p4specast, objects
from rpyp4sp.rpyjson import loads

def test_full_ast_rpython():
    currfile = os.path.abspath(__file__)
    basedir = os.path.dirname(os.path.dirname(os.path.dirname(currfile)))
    fn = os.path.join(basedir, "ast.json")
    with open(fn) as f:
        value = loads(f.read())
    defs = {}
    for i, d in enumerate(value.value_array()):
        defs[i] = p4specast.Def.fromjson(d)
        repr(defs[i])


def test_example_values_load():
    from rpyp4sp.rpyjson import loads
    import os
    currfile = os.path.abspath(__file__)
    testdir = os.path.dirname(currfile)
    fn = os.path.join(testdir, "example_values.json")
    with open(fn) as f:
        value = loads(f.read())
    res = objects.BaseV.fromjson(value)
