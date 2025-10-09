from __future__ import print_function
import pytest

import os

from rpyp4sp.rpyjson import loads
from rpyp4sp.context import Context
from rpyp4sp import p4specast, objects, interp, rpyjson

currfile = os.path.abspath(__file__)
basedir = os.path.dirname(os.path.dirname(os.path.dirname(currfile)))
ASTFN = os.path.join(basedir, "ast.json")

def load():
    with open(ASTFN) as f:
        value = loads(f.read())
    if value.is_object:
        spec_dirname = value.get_dict_value("spec_dirname").value_string()
        file_content_json = value.get_dict_value("file_content")
        file_names_json = file_content_json.get_list_item(0)
        file_content_json = file_content_json.get_list_item(1)
        file_content = {}
        for i, name in enumerate(file_names_json.value_array()):
            file_content[name.value_string()] = file_content_json.value_array()[i].value_string()
        value = value.get_dict_value("ast")
    else:
        file_content = {}
        spec_dirname = None
    defs = []
    cache = p4specast.FromjsonCache()
    for i, d in enumerate(value.value_array()):
        defs.append(p4specast.Def.fromjson(d, cache))
    return defs, file_content, spec_dirname

def make_context(loaded=[]):
    if loaded:
        return loaded[0]
    spec, file_content, spec_dirname = load()
    ctx = Context.make0()
    ctx.load_spec(spec, file_content, spec_dirname, 'dummy')
    loaded.append(ctx)
    return ctx


def test_load_spec():
    ctx = make_context()
    assert 'Program_ok' in ctx.glbl.renv
    assert 'empty_map' in ctx.glbl.fenv

def test_subtyp_nat():
    typ = p4specast.NumT.NAT
    value = objects.NumV.fromstr('32', p4specast.IntT.INSTANCE, p4specast.NumT.INT)
    res = interp.subtyp(None, typ, value)
    assert res is True

def test_downcast_nat():
    typ = p4specast.NumT.NAT
    value = objects.NumV.fromstr('32', p4specast.IntT.INSTANCE, p4specast.NumT.INT)
    _, res = interp.downcast(None, typ, value)
    assert res.what == p4specast.NatT.INSTANCE

def test_upcast_list():
    typ = p4specast.IterT(p4specast.VarT(p4specast.Id('paramIL', p4specast.Region.line_span('spec/4g-typing-decl.watsup', 787, 32, 39)), []), p4specast.List())
    value = objects.ListV.make([], p4specast.IterT(p4specast.VarT(p4specast.Id('paramtyp', p4specast.Region.line_span('spec/2c1-runtime-type.watsup', 18, 9, 17)), []), p4specast.List()))
    _, res = interp.upcast(None, typ, value)
    assert res is value

def test_reversed_iters_list():
    res = p4specast.ReverseIterExp.from_unreversed_list([1, 2, 3])
    assert res.head == 3
    assert res.tail.head == 2
    assert res.tail.tail.head == 1
    assert res.tail.tail.tail is None
    assert repr(res) == 'ReverseIterExp.from_unreversed_list([1, 2, 3])'


def test_binop_num_sub_is_int():
    def mknat(val): return objects.NumV.fromstr(str(val), p4specast.NatT.INSTANCE, p4specast.NumT.NAT)
    res = interp.eval_binop_num('SubOp', mknat(5), mknat(9), p4specast.NumT.INT)
    assert res.what == p4specast.IntT.INSTANCE

def test_eval_arg():
    arg = p4specast.DefA(p4specast.Id('compatible_plusminusmult', p4specast.Region.line_span('spec/4e-typing-expr.watsup', 173, 84, 108)))
    ctx = make_context()
    ctx, res = interp.eval_arg(ctx, arg)


def test_coerce_binary():
    arg0 = objects.CaseV.make([objects.CaseV.make([objects.NumV.fromstr('5', p4specast.IntT.INSTANCE, p4specast.NumT.INT)], p4specast.MixOp([[p4specast.AtomT('INT', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 9, 4), p4specast.Position('spec/1a-syntax-el.watsup', 9, 7)))], []]), p4specast.VarT(p4specast.Id('num', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 8, 7), p4specast.Position('spec/1a-syntax-el.watsup', 8, 10))), [])), objects.CaseV.make([objects.CaseV.make([], p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), [])), objects.CaseV.make([], p4specast.MixOp([[p4specast.AtomT('LCTK', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 13), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 17)))]]), p4specast.VarT(p4specast.Id('ctk', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 7), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 10))), []))], p4specast.MixOp([[p4specast.AtomT('(', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 18), p4specast.Position('spec/3-syntax-il.watsup', 123, 19)))], [p4specast.AtomT(';', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 22), p4specast.Position('spec/3-syntax-il.watsup', 123, 23)))], [p4specast.AtomT(')', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 27), p4specast.Position('spec/3-syntax-il.watsup', 123, 28)))]]), p4specast.VarT(p4specast.Id('annotIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 7), p4specast.Position('spec/3-syntax-il.watsup', 123, 14))), []))], p4specast.MixOp([[p4specast.AtomT('NumE', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 128, 4), p4specast.Position('spec/3-syntax-il.watsup', 128, 8)))], [], []]), p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 124, 7), p4specast.Position('spec/3-syntax-il.watsup', 124, 13))), []))
    arg1 = objects.CaseV.make([objects.CaseV.make([objects.NumV.fromstr('3', p4specast.IntT.INSTANCE, p4specast.NumT.INT)], p4specast.MixOp([[p4specast.AtomT('INT', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 9, 4), p4specast.Position('spec/1a-syntax-el.watsup', 9, 7)))], []]), p4specast.VarT(p4specast.Id('num', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 8, 7), p4specast.Position('spec/1a-syntax-el.watsup', 8, 10))), [])), objects.CaseV.make([objects.CaseV.make([], p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), [])), objects.CaseV.make([], p4specast.MixOp([[p4specast.AtomT('LCTK', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 13), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 17)))]]), p4specast.VarT(p4specast.Id('ctk', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 7), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 10))), []))], p4specast.MixOp([[p4specast.AtomT('(', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 18), p4specast.Position('spec/3-syntax-il.watsup', 123, 19)))], [p4specast.AtomT(';', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 22), p4specast.Position('spec/3-syntax-il.watsup', 123, 23)))], [p4specast.AtomT(')', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 27), p4specast.Position('spec/3-syntax-il.watsup', 123, 28)))]]), p4specast.VarT(p4specast.Id('annotIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 7), p4specast.Position('spec/3-syntax-il.watsup', 123, 14))), []))], p4specast.MixOp([[p4specast.AtomT('NumE', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 128, 4), p4specast.Position('spec/3-syntax-il.watsup', 128, 8)))], [], []]), p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 124, 7), p4specast.Position('spec/3-syntax-il.watsup', 124, 13))), []))
    expected = objects.OptV(objects.TupleV.make([objects.CaseV.make([objects.CaseV.make([objects.NumV.fromstr('5', p4specast.IntT.INSTANCE, p4specast.NumT.INT)], p4specast.MixOp([[p4specast.AtomT('INT', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 9, 4), p4specast.Position('spec/1a-syntax-el.watsup', 9, 7)))], []]), p4specast.VarT(p4specast.Id('num', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 8, 7), p4specast.Position('spec/1a-syntax-el.watsup', 8, 10))), [])), objects.CaseV.make([objects.CaseV.make([], p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), [])), objects.CaseV.make([], p4specast.MixOp([[p4specast.AtomT('LCTK', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 13), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 17)))]]), p4specast.VarT(p4specast.Id('ctk', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 7), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 10))), []))], p4specast.MixOp([[p4specast.AtomT('(', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 18), p4specast.Position('spec/3-syntax-il.watsup', 123, 19)))], [p4specast.AtomT(';', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 22), p4specast.Position('spec/3-syntax-il.watsup', 123, 23)))], [p4specast.AtomT(')', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 27), p4specast.Position('spec/3-syntax-il.watsup', 123, 28)))]]), p4specast.VarT(p4specast.Id('annotIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 7), p4specast.Position('spec/3-syntax-il.watsup', 123, 14))), []))], p4specast.MixOp([[p4specast.AtomT('NumE', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 128, 4), p4specast.Position('spec/3-syntax-il.watsup', 128, 8)))], [], []]), p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 124, 7), p4specast.Position('spec/3-syntax-il.watsup', 124, 13))), [])), objects.CaseV.make([objects.CaseV.make([objects.NumV.fromstr('3', p4specast.IntT.INSTANCE, p4specast.NumT.INT)], p4specast.MixOp([[p4specast.AtomT('INT', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 9, 4), p4specast.Position('spec/1a-syntax-el.watsup', 9, 7)))], []]), p4specast.VarT(p4specast.Id('num', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 8, 7), p4specast.Position('spec/1a-syntax-el.watsup', 8, 10))), [])), objects.CaseV.make([objects.CaseV.make([], p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), [])), objects.CaseV.make([], p4specast.MixOp([[p4specast.AtomT('LCTK', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 13), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 17)))]]), p4specast.VarT(p4specast.Id('ctk', p4specast.Region(p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 7), p4specast.Position('spec/2f-runtime-ctk.watsup', 5, 10))), []))], p4specast.MixOp([[p4specast.AtomT('(', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 18), p4specast.Position('spec/3-syntax-il.watsup', 123, 19)))], [p4specast.AtomT(';', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 22), p4specast.Position('spec/3-syntax-il.watsup', 123, 23)))], [p4specast.AtomT(')', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 27), p4specast.Position('spec/3-syntax-il.watsup', 123, 28)))]]), p4specast.VarT(p4specast.Id('annotIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 123, 7), p4specast.Position('spec/3-syntax-il.watsup', 123, 14))), []))], p4specast.MixOp([[p4specast.AtomT('NumE', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 128, 4), p4specast.Position('spec/3-syntax-il.watsup', 128, 8)))], [], []]), p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/3-syntax-il.watsup', 124, 7), p4specast.Position('spec/3-syntax-il.watsup', 124, 13))), []))], p4specast.TupleT([p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 44, 7), p4specast.Position('spec/2b2-runtime-value.watsup', 44, 13))), []), p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 44, 7), p4specast.Position('spec/2b2-runtime-value.watsup', 44, 13))), [])])), p4specast.IterT(p4specast.TupleT([p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/4d2-typing-subtyping.watsup', 379, 38), p4specast.Position('spec/4d2-typing-subtyping.watsup', 379, 44))), []), p4specast.VarT(p4specast.Id('exprIL', p4specast.Region(p4specast.Position('spec/4d2-typing-subtyping.watsup', 379, 46), p4specast.Position('spec/4d2-typing-subtyping.watsup', 379, 52))), [])]), p4specast.Opt()))

    ctx = make_context()
    func = ctx.glbl.fenv["coerce_binary"]
    ctx, value = interp.invoke_func_def_attempt_clauses(ctx, func, [arg0, arg1])
    assert value.eq(expected)



def test_bin_plus():
    ctx = make_context()
    func = ctx.glbl.fenv["bin_plus"]
    arg0 = objects.CaseV.make([objects.NumV.fromstr('5', p4specast.IntT.INSTANCE, p4specast.NumT.INT)], p4specast.MixOp([[p4specast.AtomT('IntV', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 13, 4), p4specast.Position('spec/2b2-runtime-value.watsup', 13, 8)))], []]), p4specast.VarT(p4specast.Id('val', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 7, 7), p4specast.Position('spec/2b2-runtime-value.watsup', 7, 10))), []))

    arg1 = objects.CaseV.make([objects.NumV.fromstr('3', p4specast.IntT.INSTANCE, p4specast.NumT.INT)], p4specast.MixOp([[p4specast.AtomT('IntV', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 13, 4), p4specast.Position('spec/2b2-runtime-value.watsup', 13, 8)))], []]), p4specast.VarT(p4specast.Id('val', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 7, 7), p4specast.Position('spec/2b2-runtime-value.watsup', 7, 10))), []))

    res = objects.CaseV.make([objects.NumV.fromstr('8', p4specast.IntT.INSTANCE, p4specast.NumT.INT)], p4specast.MixOp([[p4specast.AtomT('IntV', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 13, 4), p4specast.Position('spec/2b2-runtime-value.watsup', 13, 8)))], []]), p4specast.VarT(p4specast.Id('val', p4specast.Region(p4specast.Position('spec/2b2-runtime-value.watsup', 7, 7), p4specast.Position('spec/2b2-runtime-value.watsup', 7, 10))), []))
    ctx, value = interp.invoke_func_def_attempt_clauses(ctx, func, [arg0, arg1])
    assert value.eq(res)


def test_text_exp():
    exp = p4specast.TextE('main')
    exp.typ = p4specast.TextT()
    ctx, value = interp.eval_exp(None, exp)
    expected = objects.TextV('main', p4specast.TextT())
    assert value.eq(expected)

def test_concat_text():
    input_values = [objects.ListV.make([objects.TextV('CounterType', p4specast.VarT(p4specast.Id('id', p4specast.Region(p4specast.Position('', 0, 0), p4specast.Position('', 0, 0))), [])), objects.TextV('.', p4specast.TextT()), objects.TextV('packets_and_bytes', p4specast.VarT(p4specast.Id('member', p4specast.Region(p4specast.Position('', 0, 0), p4specast.Position('', 0, 0))), []))], p4specast.IterT(p4specast.VarT(p4specast.Id('id', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 21, 7), p4specast.Position('spec/1a-syntax-el.watsup', 21, 9))), []), p4specast.List()))]
    name = 'concat_text'
    expected = objects.TextV('CounterType.packets_and_bytes', p4specast.TextT())

    ctx = make_context()
    func = ctx.glbl.fenv[name]
    ctx, value = interp.invoke_func_def_attempt_clauses(ctx, func, input_values)
    assert value.eq(expected)

def test_conse_fresh_tids():
    name = 'fresh_tids'
    input_values = [objects.NumV.fromstr('1', p4specast.NatT.INSTANCE, p4specast.NumT.NAT)]
    res = objects.ListV.make([objects.TextV('FRESH__0', p4specast.VarT(p4specast.Id('tid', p4specast.Region(p4specast.Position('', 0, 0), p4specast.Position('', 0, 0))), []))], p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region(p4specast.Position('spec/2a-runtime-domain.watsup', 13, 19), p4specast.Position('spec/2a-runtime-domain.watsup', 13, 22))), []), p4specast.List()))
    ctx = make_context()
    func = ctx.glbl.fenv[name]
    ctx, value = interp.invoke_func_def_attempt_clauses(ctx, func, input_values)
    assert value.eq(res)

def test_check_arity():
    name = 'check_arity'
    input_values = [objects.ListV.make([], p4specast.IterT(p4specast.IterT(p4specast.VarT(p4specast.Id('id', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 21, 7), p4specast.Position('spec/1a-syntax-el.watsup', 21, 9))), []), p4specast.Opt()), p4specast.List())), objects.ListV.make([], p4specast.IterT(p4specast.VarT(p4specast.Id('id', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 21, 7), p4specast.Position('spec/1a-syntax-el.watsup', 21, 9))), []), p4specast.List()))]
    res = objects.BoolV.make(True, p4specast.BoolT.INSTANCE)
    ctx = make_context()
    func = ctx.glbl.fenv[name]
    _, value = interp.invoke_func_def_attempt_clauses(ctx, func, input_values)
    assert value.eq(res)

    input_values = [objects.ListV.make([objects.OptV(None, p4specast.IterT(p4specast.VarT(p4specast.Id('id', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 21, 7), p4specast.Position('spec/1a-syntax-el.watsup', 21, 9))), []), p4specast.Opt()))], p4specast.IterT(p4specast.IterT(p4specast.VarT(p4specast.Id('id', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 21, 7), p4specast.Position('spec/1a-syntax-el.watsup', 21, 9))), []), p4specast.Opt()), p4specast.List())), objects.ListV.make([objects.TextV('p', p4specast.VarT(p4specast.Id('id', p4specast.Region(p4specast.Position('', 0, 0), p4specast.Position('', 0, 0))), []))], p4specast.IterT(p4specast.VarT(p4specast.Id('id', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 21, 7), p4specast.Position('spec/1a-syntax-el.watsup', 21, 9))), []), p4specast.List()))]
    _, value = interp.invoke_func_def_attempt_clauses(ctx, func, input_values)
    assert value.eq(res)


    res = objects.BoolV.make(False, p4specast.BoolT.INSTANCE)
    name = 'check_arity_more'
    func = ctx.glbl.fenv[name]
    _, value = interp.invoke_func_def_attempt_clauses(ctx, func, input_values)
    assert value.eq(res)

def test_eval_num_expr():
    exp = p4specast.NumE.fromstr('0', p4specast.NatT.INSTANCE)
    exp.typ = p4specast.NumT.NAT
    _, value = interp.eval_exp(None, exp)
    assert value.eq(objects.NumV.fromstr('0', p4specast.NatT.INSTANCE))

def test_type_alpha():
    input_values = [objects.CaseV.make([objects.TextV('metadata', p4specast.VarT(p4specast.Id('id', p4specast.NO_REGION), [])), objects.ListV.make([], p4specast.IterT(p4specast.TupleT([p4specast.VarT(p4specast.Id('member', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 35, 7), p4specast.Position('spec/1a-syntax-el.watsup', 35, 13))), []), p4specast.VarT(p4specast.Id('typ', p4specast.Region(p4specast.Position('spec/2c3-runtime-type-subst.watsup', 16, 29), p4specast.Position('spec/2c3-runtime-type-subst.watsup', 16, 32))), [])]), p4specast.List()))], p4specast.MixOp([[p4specast.AtomT('StructT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 66, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 66, 11)))], [], []]), p4specast.VarT(p4specast.Id('datatyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 59, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 59, 14))), [])), objects.CaseV.make([objects.TextV('metadata', p4specast.VarT(p4specast.Id('id', p4specast.NO_REGION), [])), objects.ListV.make([], p4specast.IterT(p4specast.TupleT([p4specast.VarT(p4specast.Id('member', p4specast.Region(p4specast.Position('spec/1a-syntax-el.watsup', 35, 7), p4specast.Position('spec/1a-syntax-el.watsup', 35, 13))), []), p4specast.VarT(p4specast.Id('typ', p4specast.Region(p4specast.Position('spec/2c3-runtime-type-subst.watsup', 16, 29), p4specast.Position('spec/2c3-runtime-type-subst.watsup', 16, 32))), [])]), p4specast.List()))], p4specast.MixOp([[p4specast.AtomT('StructT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 66, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 66, 11)))], [], []]), p4specast.VarT(p4specast.Id('datatyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 59, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 59, 14))), []))]
    name = 'Type_alpha'
    ctx = make_context()
    resctx, values = interp.invoke_rel(ctx, p4specast.AtomT(name, None), input_values)
    assert repr(resctx._cover) == 'Coverage(ImmutableIntSet.from_list([]), ImmutableIntSet.from_list([38, 39, 40, 41]))'
    assert values == []


def iter_all(fn):
    with open(fn, 'r') as f:
        for line in f:
            if not line.startswith('{'):
                continue
            callspec = rpyjson.loads(line)
            what = callspec.get_dict_value('calltype').value_string()
            args = callspec.get_dict_value('inputs')
            input_values = [objects.BaseV.fromjson(arg) for arg in args]
            if what == 'function':
                res_value = objects.BaseV.fromjson(callspec.get_dict_value('result'))
                yield "function", callspec.get_dict_value('name').value_string(), input_values, res_value
            elif what == 'relation':
                res_values = [objects.BaseV.fromjson(rv) for rv in callspec.get_dict_value('results').value_array()]
                yield "relation", callspec.get_dict_value('name').value_string(), input_values, res_values
            else:
                assert 0

def test_all():
    # load test cases from line-based json file
    # check if file exists
    import pytest
    if not os.path.exists(os.path.join(os.path.dirname(__file__), 'interp_tests.json')):
        pytest.skip("interp_tests.json file not found")
    ctx = make_context()
    passed = 0
    failed = 0
    error = 0
    for calltype, name, input_values, res in iter_all(os.path.join(os.path.dirname(__file__), 'interp_tests.json')):
        if calltype == "function":
            if name not in ctx.glbl.fenv:
                continue
            func = ctx.glbl.fenv[name]
            try:
                _, value = interp.invoke_func_def_attempt_clauses(ctx, func, input_values)
                if not value.eq(res):
                    failed += 1
                    print("Function test failed:", name, value, res)
                else:
                    passed += 1
                    print("Function test passed:", name)
            except Exception as e:
                #import pdb; pdb.xpm()
                error += 1
                print("Function test exception:", name, e)
                continue
        if calltype == "relation":
            try:
                _, values = interp.invoke_rel(ctx, p4specast.AtomT(name, None), input_values)
                if len(values) != len(res):
                    failed += 1
                    print("Relation test wrong number of results", name, len(values), len(res))
                else:
                    for i, resval in enumerate(values):
                        resval_exp = res[i]
                        if not resval.eq(resval_exp):
                            failed += 1
                            print("Relation test failed:", name, resval, resval_exp)
                        else:
                            passed += 1
                            print("Relation test passed:", name)
            except Exception as e:
                #import pdb; pdb.xpm()
                error += 1
                print("Relation test exception:", name, e)
                continue
    print("PASSED:", passed)
    print("FAILED", failed)
    print("ERROR ", error)
