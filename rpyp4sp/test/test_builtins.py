import pytest
from rpyp4sp import p4specast, objects, builtin, context, integers

def test_int_to_text():
    res = builtin.texts_int_to_text(None, [], [objects.NumV.fromstr('1234', p4specast.IntT.INSTANCE, p4specast.NumT.INT)])
    assert res.eq(objects.TextV('1234'))

def mkint(val):
    return objects.NumV.fromstr(str(val), p4specast.IntT.INSTANCE, p4specast.NumT.INT)

def test_shl():
    res = builtin.numerics_shl(None, [], [mkint(1234), mkint(4)])
    assert res.eq(mkint(1234 << 4))

def test_numerics_to_bitstr():
    inputs = [mkint(4), mkint(-1)]
    res = builtin.numerics_to_bitstr(None, [], inputs)
    assert res.eq(mkint(15))
    inputs = [mkint(4), mkint(20)]
    res = builtin.numerics_to_bitstr(None, [], inputs)
    assert res.eq(mkint(4))

def test_numerics_to_int():
    inputs = [mkint(4), mkint(3)]
    res = builtin.numerics_to_int(None, [], inputs)
    assert res.eq(mkint(3))
    inputs = [mkint(4), mkint(15)]
    res = builtin.numerics_to_int(None, [], inputs)
    assert res.eq(mkint(-1))

def test_numerics_bitacc():
    inputs = [mkint(699050), mkint(3), mkint(2)]
    res = builtin.numerics_bitacc(None, [], inputs)
    # 699050 in binary: 10101010101010101010
    # Extract bits 3:2 (slice_width = 3+1-2 = 2 bits)
    # Right shift by 2: 10101010101010101010 >> 2 = 0101010101010101010
    # Mask with 2^2-1 = 3 (binary 11): 0101010101010101010 & 11 = 10 = 2
    assert res.eq(mkint(2))

    # Test with 0xABCD (43981): extract bits 7:4
    inputs = [mkint(0xABCD), mkint(7), mkint(4)]
    res = builtin.numerics_bitacc(None, [], inputs)
    # 0xABCD >> 4 & ((1 << 4) - 1) = 0xABC >> 0 & 0xF = 0xC = 12
    assert res.eq(mkint(12))

    # Test extracting lower 4 bits
    inputs = [mkint(0xABCD), mkint(3), mkint(0)]
    res = builtin.numerics_bitacc(None, [], inputs)
    # 0xABCD >> 0 & ((1 << 4) - 1) = 0xABCD & 0xF = 0xD = 13
    assert res.eq(mkint(13))

def test_numerics_band():
    # Test AND operation: 12 & 10 = 8
    inputs = [mkint(12), mkint(10)]
    res = builtin.numerics_band(None, [], inputs)
    assert res.eq(mkint(8))

    inputs = [mkint(-1), mkint(255)]
    res = builtin.numerics_band(None, [], inputs)
    assert res.eq(mkint(255))

def test_numerics_bxor():
    inputs = [mkint(12), mkint(10)]
    res = builtin.numerics_bxor(None, [], inputs)
    assert res.eq(mkint(6))

    inputs = [mkint(15), mkint(15)]
    res = builtin.numerics_bxor(None, [], inputs)
    assert res.eq(mkint(0))

def test_numerics_bneg():
    inputs = [mkint(0)]
    res = builtin.numerics_bneg(None, [], inputs)
    assert res.eq(mkint(-1))

    inputs = [mkint(-1)]
    res = builtin.numerics_bneg(None, [], inputs)
    assert res.eq(mkint(0))

    inputs = [mkint(42)]
    res = builtin.numerics_bneg(None, [], inputs)
    assert res.eq(mkint(-43))


def test_numerics_bor():
    inputs = [mkint(12), mkint(10)]
    res = builtin.numerics_bor(None, [], inputs)
    assert res.eq(mkint(14))

    inputs = [mkint(42), mkint(0)]
    res = builtin.numerics_bor(None, [], inputs)
    assert res.eq(mkint(42))

def test_numerics_pow2():
    v = mkint(12)
    res = builtin.numerics_pow2(None, [], [v])
    assert res.eq(mkint(4096))

    v = mkint(0)
    res = builtin.numerics_pow2(None, [], [v])
    assert res.eq(mkint(1))

    v = mkint(-1)
    with pytest.raises(builtin.P4BuiltinError):
        res = builtin.numerics_pow2(None, [], [v])

def test_fresh():
    oldval = builtin.HOLDER.counter
    try:
        builtin.HOLDER.counter = 0 # scary global state
        res = builtin.fresh_fresh_tid(None, [], [])
        assert res.value == 'FRESH__0'
    finally:
        builtin.HOLDER.counter = oldval


def textlist(*args):
    l = [objects.TextV(arg, p4specast.TextT()) for arg in args]
    return objects.ListV(l, p4specast.IterT(p4specast.TextT(), p4specast.List()))

def test_list_rev():
    arg = textlist()
    res = builtin.lists_rev_(None, None, [arg])
    assert res is arg

    arg = textlist('a')
    res = builtin.lists_rev_(None, None, [arg])
    assert res is arg

    arg = textlist('a', 'b')
    res = builtin.lists_rev_(None, None, [arg])
    exp = textlist('b', 'a')
    assert res.eq(exp)

def test_list_distinct():
    args = [textlist()]
    res = builtin.lists_distinct_(None, None, args)
    assert res.eq(objects.BoolV(True))

    args = [textlist('a')]
    res = builtin.lists_distinct_(None, None, args)
    assert res.eq(objects.BoolV(True))

    args = [textlist('a', 'a')]
    res = builtin.lists_distinct_(None, None, args)
    assert res.eq(objects.BoolV(False))

    args = [textlist('a', 'b', 'a')]
    res = builtin.lists_distinct_(None, None, args)
    assert res.eq(objects.BoolV(False))

def test_lists_concat():
    empty = objects.ListV([], p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2a-runtime-domain.watsup', 10, 7, 10)), []), p4specast.List()), -1)
    args = [objects.ListV([empty, empty], p4specast.IterT(p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2a-runtime-domain.watsup', 10, 7, 10)), []), p4specast.List()), p4specast.List()), -1)]
    res = builtin.lists_concat_(None, None, args)
    assert res.eq(empty)
    assert repr(res.typ) == "p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2a-runtime-domain.watsup', 10, 7, 10)), []), p4specast.List.INSTANCE)"

def test_list_assoc():
    input_values = [objects.TextV('input_port', 576, p4specast.VarT(p4specast.Id('member', p4specast.NO_REGION), [])), objects.ListV([objects.TupleV([objects.TextV('input_port', 161, p4specast.VarT(p4specast.Id('member', p4specast.NO_REGION), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('FBitT', 'spec/2c1-runtime-type.watsup', 38, 4, 9)], []]), [objects.NumV.fromstr('32', p4specast.NatT.INSTANCE, 5990, p4specast.NumT.NAT)], 5991, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region.line_span('spec/2c1-runtime-type.watsup', 35, 7, 13)), []))], 47582, p4specast.TupleT([p4specast.VarT(p4specast.Id('member', p4specast.Region.line_span('spec/1a-syntax-el.watsup', 35, 7, 13)), []), p4specast.VarT(p4specast.Id('typ', p4specast.Region.line_span('spec/2c1-runtime-type.watsup', 5, 7, 10)), [])])), objects.TupleV([objects.TextV('packet_length', 167, p4specast.VarT(p4specast.Id('member', p4specast.NO_REGION), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('FBitT', 'spec/2c1-runtime-type.watsup', 38, 4, 9)], []]), [objects.NumV.fromstr('32', p4specast.NatT.INSTANCE, 6035, p4specast.NumT.NAT)], 6036, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region.line_span('spec/2c1-runtime-type.watsup', 35, 7, 13)), []))], 47583, p4specast.TupleT([p4specast.VarT(p4specast.Id('member', p4specast.Region.line_span('spec/1a-syntax-el.watsup', 35, 7, 13)), []), p4specast.VarT(p4specast.Id('typ', p4specast.Region.line_span('spec/2c1-runtime-type.watsup', 5, 7, 10)), [])])), objects.TupleV([objects.TextV('output_action', 173, p4specast.VarT(p4specast.Id('member', p4specast.NO_REGION), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('EnumT', 'spec/2c1-runtime-type.watsup', 61, 4, 9)], [], []]), [objects.TextV('ubpf_action', 152, p4specast.VarT(p4specast.Id('id', p4specast.NO_REGION), [])), objects.ListV([objects.TextV('ABORT', 153, p4specast.VarT(p4specast.Id('member', p4specast.NO_REGION), [])), objects.TextV('DROP', 154, p4specast.VarT(p4specast.Id('member', p4specast.NO_REGION), [])), objects.TextV('PASS', 155, p4specast.VarT(p4specast.Id('member', p4specast.NO_REGION), [])), objects.TextV('REDIRECT', 156, p4specast.VarT(p4specast.Id('member', p4specast.NO_REGION), []))], 5641, p4specast.IterT(p4specast.VarT(p4specast.Id('member', p4specast.Region.line_span('spec/1a-syntax-el.watsup', 35, 7, 13)), []), p4specast.List()))], 5642, p4specast.VarT(p4specast.Id('datatyp', p4specast.Region.line_span('spec/2c1-runtime-type.watsup', 59, 7, 14)), []))], 47584, p4specast.TupleT([p4specast.VarT(p4specast.Id('member', p4specast.Region.line_span('spec/1a-syntax-el.watsup', 35, 7, 13)), []), p4specast.VarT(p4specast.Id('typ', p4specast.Region.line_span('spec/2c1-runtime-type.watsup', 5, 7, 10)), [])])), objects.TupleV([objects.TextV('output_port', 178, p4specast.VarT(p4specast.Id('member', p4specast.NO_REGION), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('FBitT', 'spec/2c1-runtime-type.watsup', 38, 4, 9)], []]), [objects.NumV.fromstr('32', p4specast.NatT.INSTANCE, 6122, p4specast.NumT.NAT)], 6123, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region.line_span('spec/2c1-runtime-type.watsup', 35, 7, 13)), []))], 47585, p4specast.TupleT([p4specast.VarT(p4specast.Id('member', p4specast.Region.line_span('spec/1a-syntax-el.watsup', 35, 7, 13)), []), p4specast.VarT(p4specast.Id('typ', p4specast.Region.line_span('spec/2c1-runtime-type.watsup', 5, 7, 10)), [])])), objects.TupleV([objects.TextV('clone', 184, p4specast.VarT(p4specast.Id('member', p4specast.NO_REGION), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('BoolT', 'spec/2c1-runtime-type.watsup', 33, 4, 9)]]), [], 6133, p4specast.VarT(p4specast.Id('primtyp', p4specast.Region.line_span('spec/2c1-runtime-type.watsup', 28, 7, 14)), []))], 47586, p4specast.TupleT([p4specast.VarT(p4specast.Id('member', p4specast.Region.line_span('spec/1a-syntax-el.watsup', 35, 7, 13)), []), p4specast.VarT(p4specast.Id('typ', p4specast.Region.line_span('spec/2c1-runtime-type.watsup', 5, 7, 10)), [])])), objects.TupleV([objects.TextV('clone_port', 187, p4specast.VarT(p4specast.Id('member', p4specast.NO_REGION), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('FBitT', 'spec/2c1-runtime-type.watsup', 38, 4, 9)], []]), [objects.NumV.fromstr('32', p4specast.NatT.INSTANCE, 6177, p4specast.NumT.NAT)], 6178, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region.line_span('spec/2c1-runtime-type.watsup', 35, 7, 13)), []))], 47587, p4specast.TupleT([p4specast.VarT(p4specast.Id('member', p4specast.Region.line_span('spec/1a-syntax-el.watsup', 35, 7, 13)), []), p4specast.VarT(p4specast.Id('typ', p4specast.Region.line_span('spec/2c1-runtime-type.watsup', 5, 7, 10)), [])]))], 47588, p4specast.IterT(p4specast.TupleT([p4specast.VarT(p4specast.Id('member', p4specast.Region.line_span('spec/1a-syntax-el.watsup', 35, 7, 13)), []), p4specast.VarT(p4specast.Id('typ', p4specast.Region.line_span('spec/2c1-runtime-type.watsup', 5, 7, 10)), [])]), p4specast.List()))]
    expected = objects.OptV(objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('FBitT', 'spec/2c1-runtime-type.watsup', 38, 4, 9)], []]), [objects.NumV.fromstr('32', p4specast.NatT.INSTANCE, 5990, p4specast.NumT.NAT)], 5991, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region.line_span('spec/2c1-runtime-type.watsup', 35, 7, 13)), [])), 47589, p4specast.IterT(p4specast.VarT(p4specast.Id('typ', p4specast.Region.line_span('spec/4e-typing-expr.watsup', 787, 30, 33)), []), p4specast.Opt()))
    targs = [p4specast.VarT(p4specast.Id('member', p4specast.Region.line_span('spec/4e-typing-expr.watsup', 787, 22, 28)), []), p4specast.VarT(p4specast.Id('typ', p4specast.Region.line_span('spec/4e-typing-expr.watsup', 787, 30, 33)), [])]
    res = builtin.lists_assoc_(None, targs, input_values)
    assert res.eq(expected)

def make_set(*args):
    lst = []
    for el in args:
        value = objects.TextV(el, p4specast.TextT())
        lst.append(value)
    list_value = objects.ListV(lst, p4specast.IterT(p4specast.TextT(), p4specast.List()))
    settyp = p4specast.VarT(builtin.set_id, [p4specast.TextT()])
    return objects.CaseV(builtin.map_mixop, [list_value], settyp)


def test_union_set():
    args = [objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([], 6524, p4specast.IterT(p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 73, 24, 25)), []), p4specast.List()))], 6525, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 73, 24, 25)), [])])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('tparam', p4specast.Region.line_span('spec/1a-syntax-el.watsup', 123, 7, 13)), []), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c6-runtime-type-wellformed.watsup', 526, 29, 32)), [])]))]
    res = builtin.sets_union_set(None, None, args)
    assert res.eq(args[0])

    args = [objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([objects.TextV('H', 264, p4specast.VarT(p4specast.Id('tparam', p4specast.NO_REGION), []))], 11709, p4specast.IterT(p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 116, 13, 14)), []), p4specast.List()))], 11710, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 113, 36, 37)), [])])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([objects.TextV('H', 264, p4specast.VarT(p4specast.Id('tparam', p4specast.NO_REGION), []))], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('tparam', p4specast.Region.line_span('spec/1a-syntax-el.watsup', 123, 7, 13)), []), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c6-runtime-type-wellformed.watsup', 373, 29, 32)), [])]))]
    res = builtin.sets_union_set(None, None, args)
    exp = objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([objects.TextV('H', 264, p4specast.VarT(p4specast.Id('tparam', p4specast.NO_REGION), []))], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 116, 13, 14)), []), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 113, 36, 37)), [])]))
    assert res.eq(exp)

def test_unions_set():
    args = [objects.ListV([objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), []), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), [])])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), []), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), [])]))], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 21, 25)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), [])]), p4specast.List()))]
    res = builtin.sets_unions_set(None, [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), [])], args)
    exp = objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), []), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), [])]))
    assert res.eq(exp)

def test_diff_set():
    args = [objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([objects.TextV('H', 264, p4specast.TextT())], 11709, p4specast.IterT(p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 116, 13, 14)), []), p4specast.List()))], 11710, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 113, 36, 37)), [])])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([objects.TextV('H', 264, p4specast.TextT())], -1, p4specast.IterT(p4specast.TextT(), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c6-runtime-type-wellformed.watsup', 373, 29, 32)), [])]))]
    res = builtin.sets_diff_set(None, None, args)
    exp = objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 116, 13, 14)), []), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 113, 36, 37)), [])]))
    assert res.eq(exp)

def test_set_eq():
    res = builtin.sets_eq_set(None, None, [make_set(), make_set()])
    assert res.get_bool()
    res = builtin.sets_eq_set(None, None, [make_set("a"), make_set("a")])
    assert res.get_bool()
    res = builtin.sets_eq_set(None, None, [make_set("a"), make_set()])
    assert res.get_bool() == False
    res = builtin.sets_eq_set(None, None, [make_set("a"), make_set("b")])
    assert res.get_bool() == False

def test_intersect_set():
    # Intersection of empty sets
    res = builtin.sets_intersect_set(None, None, [make_set(), make_set()])
    assert res.eq(make_set())

    res = builtin.sets_intersect_set(None, None, [make_set("a"), make_set()])
    assert res.eq(make_set())

    res = builtin.sets_intersect_set(None, None, [make_set("a", "b"), make_set("a", "b")])
    assert res.eq(make_set("a", "b"))

    res = builtin.sets_intersect_set(None, None, [make_set("a", "b", "c"), make_set("b", "c", "d")])
    assert res.eq(make_set("b", "c"))

    res = builtin.sets_intersect_set(None, None, [make_set("a", "b"), make_set("c", "d")])
    assert res.eq(make_set())

def test_sub_set():
    res = builtin.sets_sub_set(None, None, [make_set(), make_set()])
    assert res.get_bool()
    res = builtin.sets_sub_set(None, None, [make_set(), make_set("a")])
    assert res.get_bool()

    res = builtin.sets_sub_set(None, None, [make_set("a", "b"), make_set("a", "b")])
    assert res.get_bool()

    res = builtin.sets_sub_set(None, None, [make_set("a"), make_set("a", "b")])
    assert res.get_bool()

    res = builtin.sets_sub_set(None, None, [make_set("a", "b"), make_set("a")])
    assert res.get_bool() == False
    res = builtin.sets_sub_set(None, None, [make_set("a", "b"), make_set("c", "d")])
    assert res.get_bool() == False


def make_map(*args):
    lst = []
    pairtyp = p4specast.VarT(p4specast.Id('pair', p4specast.NO_REGION), [p4specast.TextT(), p4specast.TextT()])
    for key, value in args:
        key_value = objects.TextV(key, p4specast.TextT())
        value_value = objects.TextV(value, p4specast.TextT())
        arrow = objects.CaseV(builtin.arrow_mixop, [key_value, value_value], pairtyp)
        lst.append(arrow)
    list_value = objects.ListV(lst, p4specast.IterT(pairtyp, p4specast.List()))
    maptyp = p4specast.VarT(builtin.map_id, [p4specast.TextT(), p4specast.TextT()])
    return objects.CaseV(builtin.map_mixop, [list_value], maptyp)


def test_add_map():
    map_value = make_map()
    res = builtin.maps_add_map(None, [p4specast.TextT(), p4specast.TextT()],
                               [map_value, objects.TextV("C", typ=p4specast.TextT()),
                                objects.TextV("d1", typ=p4specast.TextT())])
    assert res.eq(make_map(("C", "d1")))

    map_value = make_map(("A", "b1"), ("B", "c1"))
    res = builtin.maps_add_map(None, [p4specast.TextT(), p4specast.TextT()],
                               [map_value, objects.TextV("C", typ=p4specast.TextT()),
                                objects.TextV("d1", typ=p4specast.TextT())])
    assert res.eq(make_map(("A", "b1"), ("B", "c1"), ("C", "d1")))


    map_value = make_map(("A", "b1"), ("C", "c1"))
    res = builtin.maps_add_map(None, [p4specast.TextT(), p4specast.TextT()],
                               [map_value, objects.TextV("C", typ=p4specast.TextT()),
                                objects.TextV("d1", typ=p4specast.TextT())])
    assert res.eq(make_map(("A", "b1"), ("C", "d1")))

    map_value = make_map(("A", "b1"), ("D", "c1"))
    res = builtin.maps_add_map(None, [p4specast.TextT(), p4specast.TextT()],
                               [map_value, objects.TextV("C", typ=p4specast.TextT()),
                                objects.TextV("d1", typ=p4specast.TextT())])
    assert res.eq(make_map(("A", "b1"), ("C", "d1"), ("D", "c1")))


def test_find_maps():
    map_value1 = make_map(("A", "a1"), ("B", "b"))
    map_value2 = make_map(("A", "a2"), ("C", "x"))
    lst_value = objects.ListV([map_value1, map_value2], p4specast.IterT(map_value1.typ, p4specast.List()))

    res = builtin.maps_find_maps(None, [p4specast.TextT(), p4specast.TextT()],
                                 [lst_value, objects.TextV("C", typ=p4specast.TextT())])
    assert res.value.eq(objects.TextV("x", typ=p4specast.TextT()))
    res = builtin.maps_find_maps(None, [p4specast.TextT(), p4specast.TextT()],
                                 [lst_value, objects.TextV("A", typ=p4specast.TextT())])
    assert res.value.eq(objects.TextV("a1", typ=p4specast.TextT()))
    res = builtin.maps_find_maps(None, [p4specast.TextT(), p4specast.TextT()],
                                 [lst_value, objects.TextV("D", typ=p4specast.TextT())])
    assert res.value is None

def test_lists_partition():
    # Test partitioning an empty list
    empty_list = objects.ListV([], p4specast.IterT(p4specast.TextT(), p4specast.List()))
    len_val = objects.NumV.fromstr('0', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    res = builtin.lists_partition_(None, [p4specast.TextT()], [empty_list, len_val])
    assert isinstance(res, objects.TupleV)
    assert len(res.elements) == 2
    assert res.elements[0].eq(empty_list)
    assert res.elements[1].eq(empty_list)

    # Test partitioning at index 0 (all elements go to right)
    test_list = textlist("a", "b", "c")
    len_val = objects.NumV.fromstr('0', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    res = builtin.lists_partition_(None, [p4specast.TextT()], [test_list, len_val])
    assert isinstance(res, objects.TupleV)
    assert len(res.elements) == 2
    left_list, right_list = res.elements
    assert left_list.eq(textlist())  # empty
    assert right_list.eq(test_list)  # all elements

    # Test partitioning at index 2 (first 2 elements go to left, rest to right)
    test_list = textlist("a", "b", "c", "d")
    len_val = objects.NumV.fromstr('2', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    res = builtin.lists_partition_(None, [p4specast.TextT()], [test_list, len_val])
    assert isinstance(res, objects.TupleV)
    assert len(res.elements) == 2
    left_list, right_list = res.elements
    assert left_list.eq(textlist("a", "b"))
    assert right_list.eq(textlist("c", "d"))

    # Test partitioning with length >= list length (all elements go to left)
    test_list = textlist("x", "y")
    len_val = objects.NumV.fromstr('5', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    res = builtin.lists_partition_(None, [p4specast.TextT()], [test_list, len_val])
    assert isinstance(res, objects.TupleV)
    assert len(res.elements) == 2
    left_list, right_list = res.elements
    assert left_list.eq(test_list)  # all elements
    assert right_list.eq(textlist())  # empty

def make_text(s):
    return objects.TextV(s, -1, p4specast.TextT())

def make_nat_list(*values):
    nat_values = []
    for val in values:
        nat_values.append(objects.NumV.fromstr(str(val), p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT))
    return objects.ListV(nat_values, p4specast.IterT(p4specast.NumT.NAT, p4specast.List()))

def test_texts_strip_suffix():
    res = builtin.texts_strip_suffix(None, [], [make_text('action_list(t)'), make_text(')')])
    assert res.eq(make_text('action_list(t'))

    res = builtin.texts_strip_suffix(None, [], [make_text('hello_world'), make_text('_world')])
    assert res.eq(make_text('hello'))

    res = builtin.texts_strip_suffix(None, [], [make_text('test'), make_text('')])
    assert res.eq(make_text('test'))

    res = builtin.texts_strip_suffix(None, [], [make_text('abc'), make_text('abc')])
    assert res.eq(make_text(''))

def test_texts_strip_prefix():
    res = builtin.texts_strip_prefix(None, [], [make_text('hello_world'), make_text('hello_')])
    assert res.eq(make_text('world'))

    res = builtin.texts_strip_prefix(None, [], [make_text('test'), make_text('')])
    assert res.eq(make_text('test'))

    res = builtin.texts_strip_prefix(None, [], [make_text('abc'), make_text('abc')])
    assert res.eq(make_text(''))

def test_nats_sum():
    res = builtin.nats_sum(None, [], [make_nat_list()])
    expected = objects.NumV.fromstr('0', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_sum(None, [], [make_nat_list(42)])
    expected = objects.NumV.fromstr('42', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_sum(None, [], [make_nat_list(1, 2, 3, 4, 5)])
    expected = objects.NumV.fromstr('15', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_sum(None, [], [make_nat_list(1000000, 2000000, 3000000)])
    expected = objects.NumV.fromstr('6000000', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

def test_nats_max():
    res = builtin.nats_max(None, [], [make_nat_list(42)])
    expected = objects.NumV.fromstr('42', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_max(None, [], [make_nat_list(1, 5, 3, 2, 4)])
    expected = objects.NumV.fromstr('5', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_max(None, [], [make_nat_list(7, 3, 7, 1, 7)])
    expected = objects.NumV.fromstr('7', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_max(None, [], [make_nat_list(1000000, 5000000, 2000000)])
    expected = objects.NumV.fromstr('5000000', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    with pytest.raises(builtin.P4BuiltinError):
        builtin.nats_max(None, [], [make_nat_list()])

def test_nats_min():
    res = builtin.nats_min(None, [], [make_nat_list(42)])
    expected = objects.NumV.fromstr('42', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_min(None, [], [make_nat_list(5, 1, 3, 2, 4)])
    expected = objects.NumV.fromstr('1', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_min(None, [], [make_nat_list(7, 2, 5, 2, 9)])
    expected = objects.NumV.fromstr('2', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_min(None, [], [make_nat_list(5000000, 1000000, 2000000)])
    expected = objects.NumV.fromstr('1000000', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    with pytest.raises(builtin.P4BuiltinError):
        builtin.nats_min(None, [], [make_nat_list()])
