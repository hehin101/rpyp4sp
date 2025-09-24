from rpyp4sp.context import Context, FenvDict, TDenvDict
from rpyp4sp.error import P4ContextError
from rpyp4sp import objects, p4specast

import pytest

def test_tdenv_simple():
    ctx = Context.make0('dummy')
    id1 = p4specast.Id('id1', None)
    typdef1 = ([], p4specast.DefTyp())
    ctx2 = ctx.add_typdef_local(id1, typdef1)
    assert ctx2.find_typdef_local(id1) is typdef1
    id2 = p4specast.Id('id2', None)
    typdef2 = ([], p4specast.DefTyp())
    ctx3 = ctx2.add_typdef_local(id2, typdef2)
    assert ctx3.find_typdef_local(id1) is typdef1
    assert ctx3.find_typdef_local(id2) is typdef2

    typdef3 = ([], p4specast.DefTyp())
    ctx4 = ctx3.add_typdef_local(id2, typdef3)
    assert ctx4.find_typdef_local(id1) is typdef1
    assert ctx4.find_typdef_local(id2) is typdef3

def test_fenv_simple():
    ctx = Context.make0('dummy')
    id1 = p4specast.Id('id1', None)
    func1 = p4specast.DecD(id1, [], [], [])
    ctx2 = ctx.add_func_local(id1, func1)
    assert ctx2.find_func_local(id1) is func1
    id2 = p4specast.Id('id2', None)
    func2 = p4specast.DecD(id2, [], [], [])
    ctx3 = ctx2.add_func_local(id2, func2)
    assert ctx3.find_func_local(id1) is func1
    assert ctx3.find_func_local(id2) is func2

    func3 = p4specast.DecD(id2, [], [], [])
    ctx4 = ctx3.add_func_local(id2, func3)
    assert ctx4.find_func_local(id1) is func1
    assert ctx4.find_func_local(id2) is func3

def test_venv_simple():
    ctx = Context.make0('dummy')
    id1 = p4specast.Id('id1', None)
    value1 = objects.TextV('abc')
    ctx2 = ctx.add_value_local(id1, p4specast.IterList.EMPTY, value1)
    assert ctx2.find_value_local(id1, p4specast.IterList.EMPTY) is value1
    id2 = p4specast.Id('id2', None)
    value2 = objects.TextV('def')
    ctx3 = ctx2.add_value_local(id2, p4specast.IterList.EMPTY, value2)
    assert ctx3.find_value_local(id1, p4specast.IterList.EMPTY) is value1
    assert ctx3.find_value_local(id2, p4specast.IterList.EMPTY) is value2

    value3 = objects.TextV('ghi')
    ctx4 = ctx3.add_value_local(id2, p4specast.IterList.EMPTY, value3)
    assert ctx4.find_value_local(id1, p4specast.IterList.EMPTY) is value1
    assert ctx4.find_value_local(id2, p4specast.IterList.EMPTY) is value3

def test_tdenv_dict():
    d_empty = TDenvDict.EMPTY
    assert repr(d_empty) == "context.TDenvDict.EMPTY"
    assert str(d_empty) == "<tdenv >"

    id1 = p4specast.Id("id1", None)
    typdef1 = p4specast.DefTyp()
    d1 = d_empty.set(id1.value, typdef1)
    assert d1.get(id1.value) is typdef1

    typdef2 = p4specast.DefTyp()
    d2 = d_empty.set(id1.value, typdef2)
    assert d2.get(id1.value) is typdef2
    # check memoizing works
    assert d1._keys is d2._keys

    typdef3 = p4specast.DefTyp()
    d3 = d2.set(id1.value, typdef3)
    assert d3._keys is d2._keys
    assert repr(d3) == "context.TDenvDict.EMPTY.set('id1', p4specast.DefTyp())"
    assert str(d3) == "<tdenv 'id1': p4specast.DefTyp()>"

    id2 = p4specast.Id("id2", None)
    typdef4 = p4specast.DefTyp()
    d4 = d3.set(id2.value, typdef4)
    assert d4.get(id1.value) is typdef3
    assert d4.get(id2.value) is typdef4
    assert repr(d4) == "context.TDenvDict.EMPTY.set('id1', p4specast.DefTyp()).set('id2', p4specast.DefTyp())"
    assert str(d4) == "<tdenv 'id1': p4specast.DefTyp(), 'id2': p4specast.DefTyp()>"
    assert d4.bindings() == [(id1.value, typdef3), (id2.value, typdef4)]

def test_fenv_dict():
    d_empty = FenvDict.EMPTY
    assert repr(d_empty) == "context.FenvDict.EMPTY"
    assert str(d_empty) == "<fenv >"

    id1 = p4specast.Id("id1", None)
    func1 = p4specast.DecD(id1, [], [], [])
    d1 = d_empty.set(id1.value, func1)
    assert d1.get(id1.value) is func1

    func2 = p4specast.DecD(id1, [], [], [])
    d2 = d_empty.set(id1.value, func2)
    assert d2.get(id1.value) is func2
    # check memoizing works
    assert d1._keys is d2._keys

    func3 = p4specast.DecD(id1, [], [], [])
    d3 = d2.set(id1.value, func3)
    assert d3._keys is d2._keys
    assert repr(d3) == "context.FenvDict.EMPTY.set('id1', p4specast.DecD(p4specast.Id('id1', None), [], [], []))"
    assert str(d3) == "<fenv 'id1': p4specast.DecD(p4specast.Id('id1', None), [], [], [])>"

    id2 = p4specast.Id("id2", None)
    func4 = p4specast.DecD(id2, [], [], [])
    d4 = d3.set(id2.value, func4)
    assert d4.get(id1.value) is func3
    assert d4.get(id2.value) is func4
    assert repr(d4) == "context.FenvDict.EMPTY.set('id1', p4specast.DecD(p4specast.Id('id1', None), [], [], [])).set('id2', p4specast.DecD(p4specast.Id('id2', None), [], [], []))"
    assert str(d4) == "<fenv 'id1': p4specast.DecD(p4specast.Id('id1', None), [], [], []), 'id2': p4specast.DecD(p4specast.Id('id2', None), [], [], [])>"

def test_venv_vare_cashing(monkeypatch):
    id1 = p4specast.Id('id1', None)
    value1 = objects.TextV("abc")
    vare = p4specast.VarE(id1)
    ctx = Context.make0('dummy').add_value_local(id1, p4specast.IterList.EMPTY, value1)
    value2 = ctx.find_value_local(id1, p4specast.IterList.EMPTY, vare_cache=vare)
    assert value1 is value2
    assert vare._ctx_keys is ctx.venv_keys
    assert vare._ctx_index == 0
    monkeypatch.setattr(type(ctx.venv_keys), 'get_pos', None)
    value2 = ctx.find_value_local(id1, [], vare_cache=vare)
    assert value1 is value2


def test_context():
    empty_ctx = Context.make0("dummy")
    id1 = p4specast.Id('id1', None)
    id2 = p4specast.Id('id2', None)
    value1 = objects.TextV("abc")
    value2 = objects.TextV("def")

    # add_value_local
    ctx1 = empty_ctx.add_value_local(id1, p4specast.IterList.EMPTY, value1)
    ctx2 = ctx1.add_value_local(id2, p4specast.IterList.EMPTY, value2)
    ctx3 = empty_ctx.add_value_local(id2, p4specast.IterList.EMPTY, value2)

    # bound_value_local
    assert ctx1.bound_value_local(id1, p4specast.IterList.EMPTY)
    assert ctx2.bound_value_local(id1, p4specast.IterList.EMPTY)
    assert ctx2.bound_value_local(id2, p4specast.IterList.EMPTY)
    assert ctx3.bound_value_local(id2, p4specast.IterList.EMPTY)

    # find_value_local
    assert ctx1.find_value_local(id1, p4specast.IterList.EMPTY) is value1
    assert ctx2.find_value_local(id1, p4specast.IterList.EMPTY) is value1
    assert ctx2.find_value_local(id2, p4specast.IterList.EMPTY) is value2
    assert ctx3.find_value_local(id2, p4specast.IterList.EMPTY) is value2


    # copy_and_change
    ctx4 = ctx1.copy_and_change(venv_keys=ctx3.venv_keys, venv_values=ctx3._get_full_list())
    assert ctx4.find_value_local(id2, p4specast.IterList.EMPTY) is value2
    with pytest.raises(P4ContextError):
        ctx4.find_value_local(id1, p4specast.IterList.EMPTY)

    # localize
    ctx5 = ctx2.localize()
    with pytest.raises(P4ContextError):
        ctx5.find_value_local(id1, p4specast.IterList.EMPTY)
    with pytest.raises(P4ContextError):
        ctx5.find_value_local(id2, p4specast.IterList.EMPTY)

