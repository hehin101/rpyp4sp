from __future__ import print_function
import os
from rpyp4sp import p4specast, objects
from rpyp4sp.rpyjson import loads, JSONDecoder

def test_jsonparser():
    s = '{"calltype":"function","name":"check_func_name","inputs":[{"it":["TextV","pipe"],"note":{"vid":384,"typ":["VarT",{"it":"id","note":null,"at":{"left":{"file":"","line":0,"column":0},"right":{"file":"","line":0,"column":0}}},[]]},"at":null},{"it":["TextV","pipe"],"note":{"vid":322,"typ":["VarT",{"it":"id","note":null,"at":{"left":{"file":"","line":0,"column":0},"right":{"file":"","line":0,"column":0}}},[]]},"at":null}],"result":{"it":["BoolV",true],"note":{"vid":44492,"typ":["BoolT"]},"at":null}}'

    decoder = JSONDecoder(s)
    try:
        w_res = decoder.decode_any(0)
        i = decoder.skip_whitespace(decoder.pos)
        if i < len(s):
            start = i
            end = len(s) - 1
            assert False, 'extra data'
    finally:
        decoder.close()
    assert w_res.is_object

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
