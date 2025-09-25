import pytest
from rpyp4sp import p4specast, objects, interp, rpyjson


def test_compare_casev():
    self = objects.CaseV.make([], p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), []), 100)
    other = objects.CaseV.make([], p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), []), 111)
    res = self.compare(other)
    assert res == 0

def make_atom(value):
    # Helper to create AtomT with dummy region
    region = p4specast.Region(p4specast.Position('', 0, 0), p4specast.Position('', 0, 0))
    return p4specast.AtomT(value, region)

def test_mixop_compare_equal():
    a = p4specast.MixOp([[make_atom('A'), make_atom('B')], [make_atom('C')]])
    b = p4specast.MixOp([[make_atom('A'), make_atom('B')], [make_atom('C')]])
    assert a.compare(b) == 0
    assert b.compare(a) == 0

def test_mixop_compare_less():
    a = p4specast.MixOp([[make_atom('A')]])
    b = p4specast.MixOp([[make_atom('B')]])
    assert a.compare(b) == -1
    assert b.compare(a) == 1

def test_mixop_compare_phrase_length():
    a = p4specast.MixOp([[make_atom('A')]])
    b = p4specast.MixOp([[make_atom('A'), make_atom('B')]])
    assert a.compare(b) == -1
    assert b.compare(a) == 1

def test_mixop_compare_phrases_length():
    a = p4specast.MixOp([[make_atom('A')]])
    b = p4specast.MixOp([[make_atom('A')], [make_atom('B')]])
    assert a.compare(b) == -1
    assert b.compare(a) == 1

def test_mixop_compare_complex():
    a = p4specast.MixOp([[make_atom('A'), make_atom('B')], [make_atom('C')]])
    b = p4specast.MixOp([[make_atom('A'), make_atom('B')], [make_atom('D')]])
    assert a.compare(b) == -1
    assert b.compare(a) == 1

