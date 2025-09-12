import pytest
from rpyp4sp import p4specast, objects, interp, rpyjson


def test_compare_casev():
    self = objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), [], 100, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), []))
    other = objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), [], 111, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), []))
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

def test_compare_structv():
    a = objects.StructV([(p4specast.AtomT('SIZE', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 18, 4), p4specast.Position('spec/4a2-typing-tblctx.watsup', 18, 8))), objects.NumV.fromstr('0', 'Int', -1, p4specast.NumT(p4specast.IntT()))), (p4specast.AtomT('CONST', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 19, 4), p4specast.Position('spec/4a2-typing-tblctx.watsup', 19, 9))), objects.BoolV(True, -1, p4specast.BoolT()))], -1, p4specast.VarT(p4specast.Id('entry', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 53, 17), p4specast.Position('spec/4a2-typing-tblctx.watsup', 53, 22))), []))
    b = objects.StructV([(p4specast.AtomT('SIZE', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 18, 4), p4specast.Position('spec/4a2-typing-tblctx.watsup', 18, 8))), objects.NumV.fromstr('0', 'Int', 568, p4specast.NumT(p4specast.IntT()))), (p4specast.AtomT('CONST', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 19, 4), p4specast.Position('spec/4a2-typing-tblctx.watsup', 19, 9))), objects.BoolV(True, 569, p4specast.BoolT()))], 570, p4specast.VarT(p4specast.Id('entry', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 53, 17), p4specast.Position('spec/4a2-typing-tblctx.watsup', 53, 22))), []))
    assert a.compare(b) == 0

    a = objects.StructV([(p4specast.AtomT('a', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 18, 4), p4specast.Position('spec/4a2-typing-tblctx.watsup', 18, 8))), objects.NumV.fromstr('0', 'Int', -1, p4specast.NumT(p4specast.IntT()))), (p4specast.AtomT('CONST', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 19, 4), p4specast.Position('spec/4a2-typing-tblctx.watsup', 19, 9))), objects.BoolV(True, -1, p4specast.BoolT()))], -1, p4specast.VarT(p4specast.Id('entry', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 53, 17), p4specast.Position('spec/4a2-typing-tblctx.watsup', 53, 22))), []))
    b = objects.StructV([(p4specast.AtomT('b', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 18, 4), p4specast.Position('spec/4a2-typing-tblctx.watsup', 18, 8))), objects.NumV.fromstr('0', 'Int', 568, p4specast.NumT(p4specast.IntT()))), (p4specast.AtomT('CONST', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 19, 4), p4specast.Position('spec/4a2-typing-tblctx.watsup', 19, 9))), objects.BoolV(True, 569, p4specast.BoolT()))], 570, p4specast.VarT(p4specast.Id('entry', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 53, 17), p4specast.Position('spec/4a2-typing-tblctx.watsup', 53, 22))), []))
    assert a.compare(b) == -1

    a = objects.StructV([(p4specast.AtomT('SIZE', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 18, 4), p4specast.Position('spec/4a2-typing-tblctx.watsup', 18, 8))), objects.NumV.fromstr('0', 'Int', -1, p4specast.NumT(p4specast.IntT()))), (p4specast.AtomT('x', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 19, 4), p4specast.Position('spec/4a2-typing-tblctx.watsup', 19, 9))), objects.BoolV(True, -1, p4specast.BoolT()))], -1, p4specast.VarT(p4specast.Id('entry', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 53, 17), p4specast.Position('spec/4a2-typing-tblctx.watsup', 53, 22))), []))
    b = objects.StructV([(p4specast.AtomT('SIZE', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 18, 4), p4specast.Position('spec/4a2-typing-tblctx.watsup', 18, 8))), objects.NumV.fromstr('0', 'Int', 568, p4specast.NumT(p4specast.IntT()))), (p4specast.AtomT('b', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 19, 4), p4specast.Position('spec/4a2-typing-tblctx.watsup', 19, 9))), objects.BoolV(True, 569, p4specast.BoolT()))], 570, p4specast.VarT(p4specast.Id('entry', p4specast.Region(p4specast.Position('spec/4a2-typing-tblctx.watsup', 53, 17), p4specast.Position('spec/4a2-typing-tblctx.watsup', 53, 22))), []))
    assert a.compare(b) == 1
