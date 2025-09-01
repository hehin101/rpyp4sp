import os
from rpyp4sp.rpyjson import loads
from rpyp4sp.context import Context
from rpyp4sp import p4specast, objects

def load():
    currfile = os.path.abspath(__file__)
    basedir = os.path.dirname(os.path.dirname(os.path.dirname(currfile)))
    fn = os.path.join(basedir, "ast.json")
    with open(fn) as f:
        value = loads(f.read())
    defs = []
    for i, d in enumerate(value.value_array()):
        defs.append(p4specast.Def.fromjson(d))
    return defs

def test_load_spec():
    spec = load()
    ctx = Context('dummy')
    ctx.load_spec(spec)
    assert 'Prog_ok' in ctx.glbl.renv
    assert 'is_fbitt' in ctx.glbl.fenv
