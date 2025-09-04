import os
from rpyp4sp.rpyjson import loads
from rpyp4sp.context import Context
from rpyp4sp import p4specast, objects, interp

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
    print(ctx.glbl.fenv["is_fbitt"])
    
def test_is_fbitt():
    # dec $is_fbitt(typ) : bool
    #     hint(show % IS FBIT_T)
    # def $is_fbitt(FBitT _) = true
    # def $is_fbitt(typ) = false
    #   -- otherwise
    spec = load()

    # returns False
    ctx = Context('dummy')
    ctx.load_spec(spec)
    func = ctx.glbl.fenv["is_fbitt"]
    arg = objects.W_CaseV(p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(left=p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), right=p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), [], 432, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(left=p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), right=p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), []))
    ctx.local.venv['typ'] = arg # TODO: will be done by assign_args later
    ctx, value = interp.invoke_func_def_attempt_clauses(ctx, func, [arg])
    assert value.get_bool() == False

