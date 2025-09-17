from rpyp4sp.context import Context, VenvDict
from rpyp4sp import objects, p4specast

import pytest

def test_venv_simple():
    ctx = Context('dummy')
    id1 = p4specast.Id('id1', None)
    value1 = objects.TextV('abc')
    ctx2 = ctx.add_value_local(id1, [], value1)
    assert ctx2.find_value_local(id1, []) is value1
    id2 = p4specast.Id('id2', None)
    value2 = objects.TextV('def')
    ctx3 = ctx2.add_value_local(id2, [], value2)
    assert ctx3.find_value_local(id1, []) is value1
    assert ctx3.find_value_local(id2, []) is value2

    value3 = objects.TextV('ghi')
    ctx4 = ctx3.add_value_local(id2, [], value3)
    assert ctx4.find_value_local(id1, []) is value1
    assert ctx4.find_value_local(id2, []) is value3

def test_venv_dict():
    d_empty = VenvDict()
    value1 = objects.TextV('abc')
    d2 = d_empty.set("a", "", value1)
    assert d2.get("a", "") is value1

    value2 = objects.TextV('def')
    d3 = d_empty.set("a", "", value2)
    assert d3.get("a", "") is value2
    # check memoizing works
    assert d2._keys is d3._keys

    value3 = objects.TextV('ghi')
    d4 = d3.set("a", "", value3)
    assert d4.get("a", "") is value3
    assert d4._keys is d3._keys
    assert repr(d4._keys) == "context.VENV_KEYS_ROOT.add_key('a', '')"
    assert str(d4._keys) == "<keys 'a'>"

    value4 = objects.TextV('jkl')
    d5 = d4.set("b", "", value4)
    assert d5.get("a", "") is value3
    assert d5.get("b", "") is value4
    assert repr(d5._keys) == "context.VENV_KEYS_ROOT.add_key('a', '').add_key('b', '')"
    assert str(d5._keys) == "<keys 'a', 'b'>"


@pytest.mark.skip
def test_context():
    # copy_and_change

    # localize

    # fidn_value_local

    # bound_value_local

    # add_value_local

    pass
