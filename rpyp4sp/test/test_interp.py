import os
from rpyp4sp.rpyjson import loads
from rpyp4sp.context import Context
from rpyp4sp import p4specast, objects, interp, rpyjson

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
    arg = objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(left=p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), right=p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), [], 432, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(left=p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), right=p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), []))
    ctx, value = interp.invoke_func_def_attempt_clauses(ctx, func, [arg])
    assert value.get_bool() == False

    ctx = Context('dummy')
    ctx.load_spec(spec)
    noposition = p4specast.Position('', 0, 0)
    noregion = p4specast.Region(noposition, noposition)

    arg = objects.CaseV(p4specast.MixOp([[p4specast.AtomT('FBitT', noregion)], []]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('BinE', noregion)], [], [], []]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('PLUS', noregion)]]), [], 1, p4specast.VarT(p4specast.Id('binop', noregion), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('NumE', noregion)], []]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('INT', noregion)], []]), [objects.NumV.fromstr('5', 'Int', 2, p4specast.NumT(p4specast.IntT()))], 3, p4specast.VarT(p4specast.Id('num', noregion), []))], 4, p4specast.VarT(p4specast.Id('expr', noregion), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('NumE', noregion)], []]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('INT', noregion)], []]), [objects.NumV.fromstr('3', 'Int', 5, p4specast.NumT(p4specast.IntT()))], 6, p4specast.VarT(p4specast.Id('num', noregion), []))], 7, p4specast.VarT(p4specast.Id('expr', noregion), []))], 8, p4specast.VarT(p4specast.Id('expr', noregion), []))], 9, p4specast.VarT(p4specast.Id('type', noregion), []))
    ctx, value = interp.invoke_func_def_attempt_clauses(ctx, func, [arg])

def test_coerce_binary():
    arg0 = objects.CaseV(p4specast.MixOp([[p4specast.AtomT('NumE', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 128, 4), p4specast.Position('spec/3-syntax-il.watsup', 128, 8)))], [], []]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('INT', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 9, 4), p4specast.Position('spec/1a-syntax-el.watsup', 9, 7)))], []]), [objects.NumV.fromstr('5', 'Int', 2, p4specast.NumT(p4specast.IntT()))], 99, p4specast.VarT(p4specast.Id('num', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 8, 7), p4specast.Position('spec/1a-syntax-el.watsup', 8, 10))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('(', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 18), p4specast.Position('spec/3-syntax-il.watsup', 123, 19)))], [p4specast.AtomT(';', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 22), p4specast.Position('spec/3-syntax-il.watsup', 123, 23)))], [p4specast.AtomT(')', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 27), p4specast.Position('spec/3-syntax-il.watsup', 123, 28)))]]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), [], 100, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('LCTK', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 13), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 17)))]]), [], 101, p4specast.VarT(p4specast.Id('ctk', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 7), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 10))), []))], 102, p4specast.VarT(p4specast.Id('annotIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 7), p4specast.Position('spec/3-syntax-il.watsup', 123, 14))), []))], 103, p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 124, 7), p4specast.Position('spec/3-syntax-il.watsup', 124, 13))), []))
    arg1 = objects.CaseV(p4specast.MixOp([[p4specast.AtomT('NumE', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 128, 4), p4specast.Position('spec/3-syntax-il.watsup', 128, 8)))], [], []]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('INT', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 9, 4), p4specast.Position('spec/1a-syntax-el.watsup', 9, 7)))], []]), [objects.NumV.fromstr('3', 'Int', 5, p4specast.NumT(p4specast.IntT()))], 110, p4specast.VarT(p4specast.Id('num', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 8, 7), p4specast.Position('spec/1a-syntax-el.watsup', 8, 10))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('(', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 18), p4specast.Position('spec/3-syntax-il.watsup', 123, 19)))], [p4specast.AtomT(';', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 22), p4specast.Position('spec/3-syntax-il.watsup', 123, 23)))], [p4specast.AtomT(')', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 27), p4specast.Position('spec/3-syntax-il.watsup', 123, 28)))]]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), [], 111, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('LCTK', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 13), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 17)))]]), [], 112, p4specast.VarT(p4specast.Id('ctk', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 7), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 10))), []))], 113, p4specast.VarT(p4specast.Id('annotIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 7), p4specast.Position('spec/3-syntax-il.watsup', 123, 14))), []))], 114, p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 124, 7), p4specast.Position('spec/3-syntax-il.watsup', 124, 13))), []))
    expected = objects.OptV(objects.TupleV([objects.CaseV(p4specast.MixOp([[p4specast.AtomT('NumE', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 128, 4), p4specast.Position('spec/3-syntax-il.watsup', 128, 8)))], [], []]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('INT', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 9, 4), p4specast.Position('spec/1a-syntax-el.watsup', 9, 7)))], []]), [objects.NumV.fromstr('5', 'Int', 2, p4specast.NumT(p4specast.IntT()))], 99, p4specast.VarT(p4specast.Id('num', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 8, 7), p4specast.Position('spec/1a-syntax-el.watsup', 8, 10))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('(', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 18), p4specast.Position('spec/3-syntax-il.watsup', 123, 19)))], [p4specast.AtomT(';', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 22), p4specast.Position('spec/3-syntax-il.watsup', 123, 23)))], [p4specast.AtomT(')', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 27), p4specast.Position('spec/3-syntax-il.watsup', 123, 28)))]]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), [], 100, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('LCTK', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 13), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 17)))]]), [], 101, p4specast.VarT(p4specast.Id('ctk', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 7), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 10))), []))], 102, p4specast.VarT(p4specast.Id('annotIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 7), p4specast.Position('spec/3-syntax-il.watsup', 123, 14))), []))], 103, p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 124, 7), p4specast.Position('spec/3-syntax-il.watsup', 124, 13))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('NumE', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 128, 4), p4specast.Position('spec/3-syntax-il.watsup', 128, 8)))], [], []]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('INT', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 9, 4), p4specast.Position('spec/1a-syntax-el.watsup', 9, 7)))], []]), [objects.NumV.fromstr('3', 'Int', 5, p4specast.NumT(p4specast.IntT()))], 110, p4specast.VarT(p4specast.Id('num', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 8, 7), p4specast.Position('spec/1a-syntax-el.watsup', 8, 10))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('(', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 18), p4specast.Position('spec/3-syntax-il.watsup', 123, 19)))], [p4specast.AtomT(';', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 22), p4specast.Position('spec/3-syntax-il.watsup', 123, 23)))], [p4specast.AtomT(')', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 27), p4specast.Position('spec/3-syntax-il.watsup', 123, 28)))]]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), [], 111, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('LCTK', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 13), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 17)))]]), [], 112, p4specast.VarT(p4specast.Id('ctk', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 7), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 10))), []))], 113, p4specast.VarT(p4specast.Id('annotIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 7), p4specast.Position('spec/3-syntax-il.watsup', 123, 14))), []))], 114, p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 124, 7), p4specast.Position('spec/3-syntax-il.watsup', 124, 13))), []))], 131, p4specast.TupleT([p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 44, 7), p4specast.Position('spec/2b2-runtime-value.watsup', 44, 13))), []), p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 44, 7), p4specast.Position('spec/2b2-runtime-value.watsup', 44, 13))), [])])), 132, p4specast.IterT(p4specast.TupleT([p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/4d2-typing-subtyping.watsup', 379, 38), p4specast.Position('spec/4d2-typing-subtyping.watsup', 379, 44))), []), p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/4d2-typing-subtyping.watsup', 379, 46), p4specast.Position('spec/4d2-typing-subtyping.watsup', 379, 52))), [])]), p4specast.Opt()))
    spec = load()

    ctx = Context('dummy')
    ctx.load_spec(spec)
    func = ctx.glbl.fenv["coerce_binary"]
    ctx, value = interp.invoke_func_def_attempt_clauses(ctx, func, [arg0, arg1])
    assert value.eq(expected)

def test_reduce_senums_binary():
    arg0 = objects.CaseV(p4specast.MixOp([[p4specast.AtomT('NumE', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 128, 4), p4specast.Position('spec/3-syntax-il.watsup', 128, 8)))], [], []]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('INT', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 9, 4), p4specast.Position('spec/1a-syntax-el.watsup', 9, 7)))], []]), [objects.NumV.fromstr('5', 'Int', 2, p4specast.NumT(p4specast.IntT()))], 99, p4specast.VarT(p4specast.Id('num', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 8, 7), p4specast.Position('spec/1a-syntax-el.watsup', 8, 10))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('(', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 18), p4specast.Position('spec/3-syntax-il.watsup', 123, 19)))], [p4specast.AtomT(';', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 22), p4specast.Position('spec/3-syntax-il.watsup', 123, 23)))], [p4specast.AtomT(')', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 27), p4specast.Position('spec/3-syntax-il.watsup', 123, 28)))]]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), [], 100, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('LCTK', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 13), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 17)))]]), [], 101, p4specast.VarT(p4specast.Id('ctk', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 7), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 10))), []))], 102, p4specast.VarT(p4specast.Id('annotIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 7), p4specast.Position('spec/3-syntax-il.watsup', 123, 14))), []))], 103, p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 124, 7), p4specast.Position('spec/3-syntax-il.watsup', 124, 13))), []))
    arg1 = objects.CaseV(p4specast.MixOp([[p4specast.AtomT('NumE', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 128, 4), p4specast.Position('spec/3-syntax-il.watsup', 128, 8)))], [], []]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('INT', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 9, 4), p4specast.Position('spec/1a-syntax-el.watsup', 9, 7)))], []]), [objects.NumV.fromstr('3', 'Int', 5, p4specast.NumT(p4specast.IntT()))], 110, p4specast.VarT(p4specast.Id('num', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 8, 7), p4specast.Position('spec/1a-syntax-el.watsup', 8, 10))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('(', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 18), p4specast.Position('spec/3-syntax-il.watsup', 123, 19)))], [p4specast.AtomT(';', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 22), p4specast.Position('spec/3-syntax-il.watsup', 123, 23)))], [p4specast.AtomT(')', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 27), p4specast.Position('spec/3-syntax-il.watsup', 123, 28)))]]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), [], 111, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('LCTK', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 13), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 17)))]]), [], 112, p4specast.VarT(p4specast.Id('ctk', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 7), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 10))), []))], 113, p4specast.VarT(p4specast.Id('annotIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 7), p4specast.Position('spec/3-syntax-il.watsup', 123, 14))), []))], 114, p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 124, 7), p4specast.Position('spec/3-syntax-il.watsup', 124, 13))), []))
    arg2 = objects.FuncV(p4specast.Id('compatible_plusminusmult', p4specast.Region(p4specast.Position('spec/4e-typing-expr.watsup', 173, 84), p4specast.Position('spec/4e-typing-expr.watsup', 173, 108))), 137, p4specast.FuncT())
    expected = objects.OptV(objects.TupleV([objects.CaseV(p4specast.MixOp([[p4specast.AtomT('NumE', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 128, 4), p4specast.Position('spec/3-syntax-il.watsup', 128, 8)))], [], []]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('INT', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 9, 4), p4specast.Position('spec/1a-syntax-el.watsup', 9, 7)))], []]), [objects.NumV.fromstr('5', 'Int', 2, p4specast.NumT(p4specast.IntT()))], 99, p4specast.VarT(p4specast.Id('num', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 8, 7), p4specast.Position('spec/1a-syntax-el.watsup', 8, 10))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('(', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 18), p4specast.Position('spec/3-syntax-il.watsup', 123, 19)))], [p4specast.AtomT(';', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 22), p4specast.Position('spec/3-syntax-il.watsup', 123, 23)))], [p4specast.AtomT(')', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 27), p4specast.Position('spec/3-syntax-il.watsup', 123, 28)))]]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), [], 100, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('LCTK', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 13), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 17)))]]), [], 101, p4specast.VarT(p4specast.Id('ctk', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 7), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 10))), []))], 102, p4specast.VarT(p4specast.Id('annotIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 7), p4specast.Position('spec/3-syntax-il.watsup', 123, 14))), []))], 103, p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 124, 7), p4specast.Position('spec/3-syntax-il.watsup', 124, 13))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('NumE', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 128, 4), p4specast.Position('spec/3-syntax-il.watsup', 128, 8)))], [], []]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('INT', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 9, 4), p4specast.Position('spec/1a-syntax-el.watsup', 9, 7)))], []]), [objects.NumV.fromstr('3', 'Int', 5, p4specast.NumT(p4specast.IntT()))], 110, p4specast.VarT(p4specast.Id('num', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 8, 7), p4specast.Position('spec/1a-syntax-el.watsup', 8, 10))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('(', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 18), p4specast.Position('spec/3-syntax-il.watsup', 123, 19)))], [p4specast.AtomT(';', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 22), p4specast.Position('spec/3-syntax-il.watsup', 123, 23)))], [p4specast.AtomT(')', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 27), p4specast.Position('spec/3-syntax-il.watsup', 123, 28)))]]), [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), [], 111, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('LCTK', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 13), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 17)))]]), [], 112, p4specast.VarT(p4specast.Id('ctk', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 7), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 10))), []))], 113, p4specast.VarT(p4specast.Id('annotIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 7), p4specast.Position('spec/3-syntax-il.watsup', 123, 14))), []))], 114, p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 124, 7), p4specast.Position('spec/3-syntax-il.watsup', 124, 13))), []))], 161, p4specast.TupleT([p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 44, 7), p4specast.Position('spec/2b2-runtime-value.watsup', 44, 13))), []), p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 44, 7), p4specast.Position('spec/2b2-runtime-value.watsup', 44, 13))), [])])), 162, p4specast.IterT(p4specast.TupleT([p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/4d2-typing-subtyping.watsup', 330, 81), p4specast.Position('spec/4d2-typing-subtyping.watsup', 330, 87))), []), p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/4d2-typing-subtyping.watsup', 330, 89), p4specast.Position('spec/4d2-typing-subtyping.watsup', 330, 95))), [])]), p4specast.Opt()))
    spec = load()

    ctx = Context('dummy')
    ctx.load_spec(spec)
    func = ctx.glbl.fenv["reduce_senums_binary"]
    ctx, value = interp.invoke_func_def_attempt_clauses(ctx, func, [arg0, arg1, arg2])

    assert value.eq(expected)



def test_empty_context():
    spec = load()
    ctx = Context('dummy')
    ctx.load_spec(spec)
    func = ctx.glbl.fenv["empty_context"]
    ctx, value = interp.invoke_func_def_attempt_clauses(ctx, func, [])


def test_bin_plus():
    spec = load()
    ctx = Context('dummy')
    ctx.load_spec(spec)
    func = ctx.glbl.fenv["bin_plus"]
    arg0 = objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntV', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 13, 4), p4specast.Position('spec/2b2-runtime-value.watsup', 13, 8)))], []]), [objects.NumV.fromstr('5', 'Int', 2, p4specast.NumT(p4specast.IntT()))], 220, p4specast.VarT(p4specast.Id('val', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 7, 7), p4specast.Position('spec/2b2-runtime-value.watsup', 7, 10))), []))

    arg1 = objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntV', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 13, 4), p4specast.Position('spec/2b2-runtime-value.watsup', 13, 8)))], []]), [objects.NumV.fromstr('3', 'Int', 5, p4specast.NumT(p4specast.IntT()))], 231, p4specast.VarT(p4specast.Id('val', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 7, 7), p4specast.Position('spec/2b2-runtime-value.watsup', 7, 10))), []))

    res = objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntV', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 13, 4), p4specast.Position('spec/2b2-runtime-value.watsup', 13, 8)))], []]), [objects.NumV.fromstr('8', 'Int', 240, p4specast.NumT(p4specast.IntT()))], 241, p4specast.VarT(p4specast.Id('val', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 7, 7), p4specast.Position('spec/2b2-runtime-value.watsup', 7, 10))), []))
    ctx, value = interp.invoke_func_def_attempt_clauses(ctx, func, [arg0, arg1])
    assert value.eq(res)

def test_cast_int():
    args = [objects.CaseV(p4specast.MixOp([[p4specast.AtomT('FBitT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 38, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 38, 9)))], []]), [objects.NumV.fromstr('8', 'Nat', 247, p4specast.NumT(p4specast.NatT()))], 248, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), [])), objects.NumV.fromstr('10', 'Int', 10, p4specast.NumT(p4specast.IntT()))]
    name = "cast_int'"
    spec = load()
    ctx = Context('dummy')
    ctx.load_spec(spec)
    func = ctx.glbl.fenv[name]
    ctx, value = interp.invoke_func_def_attempt_clauses(ctx, func, args)
    expected = objects.CaseV(p4specast.MixOp([[p4specast.AtomT('FBitV', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 15, 4), p4specast.Position('spec/2b2-runtime-value.watsup', 15, 9)))], [], []]), [objects.NumV.fromstr('8', 'Nat', 247, p4specast.NumT(p4specast.NatT())), objects.NumV.fromstr('10', 'Int', 370, p4specast.NumT(p4specast.IntT()))], 371, p4specast.VarT(p4specast.Id('val', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 7, 7), p4specast.Position('spec/2b2-runtime-value.watsup', 7, 10))), []))
    assert value.eq(expected)


def test_assign_exp():
    # TODO: incomplete, what do we actually expect?
    ctx = Context('dummy')
    exp = p4specast.IterE(p4specast.VarE(p4specast.Id('text', p4specast.Region(p4specast.Position('spec/0-aux.watsup', 32, 17), p4specast.Position('spec/0-aux.watsup', 32, 20)))), p4specast.List(), [p4specast.Var(id=p4specast.Id('text', p4specast.Region(p4specast.Position('spec/0-aux.watsup', 32, 17), p4specast.Position('spec/0-aux.watsup', 32, 20))), typ=p4specast.TextT(), iter=[])])
    value = objects.ListV([], 1540, p4specast.IterT(p4specast.TextT(), p4specast.List()))
    ctx_returned = interp.assign_exp(ctx, exp, value)
    print(ctx_returned)

def test_all():
    # load test cases from line-based json file
    func_cases = []
    relation_cases = []
    # check if file exists
    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'interp_tests_bak.json')):
        assert False
    with open(os.path.join(os.path.dirname(__file__), 'interp_tests_bak.json'), 'r') as f:
        for line in f:
            if not line.startswith('{'):
                continue
            callspec = rpyjson.loads(line)
            what = callspec['calltype'].value_string()
            args = callspec['inputs']
            input_values = [objects.BaseV.fromjson(arg) for arg in args]
            if what == 'function':
                res_value = objects.BaseV.fromjson(callspec['result'])
                func_cases.append((callspec['name'].value_string(), input_values, res_value))
            elif what == 'relation':
                res_values = [objects.BaseV.fromjson(rv) for rv in callspec['results']]
                relation_cases.append((callspec['name'].value_string(), input_values, res_values))
            else:
                assert 0
    spec = load()
    ctx = Context('dummy')
    ctx.load_spec(spec)
    for name, input_values, res_value in func_cases:
        if name not in ctx.glbl.fenv:
            continue
        func = ctx.glbl.fenv[name]
        try:
            ctx, value = interp.invoke_func_def_attempt_clauses(ctx, func, input_values)
            if not value.eq(res_value):
                print("Function test failed:", name, value, res_value)
            else:
                print("Function test passed:", name)
        except Exception as e:
            #import pdb; pdb.xpm()
            print("Function test exception:", name, e)
            continue
