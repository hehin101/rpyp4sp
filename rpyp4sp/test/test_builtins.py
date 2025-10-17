import pytest
from rpyp4sp import p4specast, objects, builtin, context, integers

def mktext(val):
    return objects.TextV(val, p4specast.TextT.INSTANCE)

def test_int_to_text():
    res = builtin.texts_int_to_text([], [objects.NumV.fromstr('1234', p4specast.IntT.INSTANCE, p4specast.NumT.INT)])
    assert res.eq(mktext('1234'))

def mkint(val):
    return objects.NumV.fromstr(str(val), p4specast.IntT.INSTANCE, p4specast.NumT.INT)

def test_shl():
    res = builtin.numerics_shl([], [mkint(1234), mkint(4)])
    assert res.eq(mkint(1234 << 4))

def test_numerics_to_bitstr():
    inputs = [mkint(4), mkint(-1)]
    res = builtin.numerics_to_bitstr([], inputs)
    assert res.eq(mkint(15))
    inputs = [mkint(4), mkint(20)]
    res = builtin.numerics_to_bitstr([], inputs)
    assert res.eq(mkint(4))

def test_numerics_to_int():
    inputs = [mkint(4), mkint(3)]
    res = builtin.numerics_to_int([], inputs)
    assert res.eq(mkint(3))
    inputs = [mkint(4), mkint(15)]
    res = builtin.numerics_to_int([], inputs)
    assert res.eq(mkint(-1))

def test_numerics_bitacc():
    inputs = [mkint(699050), mkint(3), mkint(2)]
    res = builtin.numerics_bitacc([], inputs)
    # 699050 in binary: 10101010101010101010
    # Extract bits 3:2 (slice_width = 3+1-2 = 2 bits)
    # Right shift by 2: 10101010101010101010 >> 2 = 0101010101010101010
    # Mask with 2^2-1 = 3 (binary 11): 0101010101010101010 & 11 = 10 = 2
    assert res.eq(mkint(2))

    # Test with 0xABCD (43981): extract bits 7:4
    inputs = [mkint(0xABCD), mkint(7), mkint(4)]
    res = builtin.numerics_bitacc([], inputs)
    # 0xABCD >> 4 & ((1 << 4) - 1) = 0xABC >> 0 & 0xF = 0xC = 12
    assert res.eq(mkint(12))

    # Test extracting lower 4 bits
    inputs = [mkint(0xABCD), mkint(3), mkint(0)]
    res = builtin.numerics_bitacc([], inputs)
    # 0xABCD >> 0 & ((1 << 4) - 1) = 0xABCD & 0xF = 0xD = 13
    assert res.eq(mkint(13))

def test_numerics_band():
    # Test AND operation: 12 & 10 = 8
    inputs = [mkint(12), mkint(10)]
    res = builtin.numerics_band([], inputs)
    assert res.eq(mkint(8))

    inputs = [mkint(-1), mkint(255)]
    res = builtin.numerics_band([], inputs)
    assert res.eq(mkint(255))

def test_numerics_bxor():
    inputs = [mkint(12), mkint(10)]
    res = builtin.numerics_bxor([], inputs)
    assert res.eq(mkint(6))

    inputs = [mkint(15), mkint(15)]
    res = builtin.numerics_bxor([], inputs)
    assert res.eq(mkint(0))

def test_numerics_bneg():
    inputs = [mkint(0)]
    res = builtin.numerics_bneg([], inputs)
    assert res.eq(mkint(-1))

    inputs = [mkint(-1)]
    res = builtin.numerics_bneg([], inputs)
    assert res.eq(mkint(0))

    inputs = [mkint(42)]
    res = builtin.numerics_bneg([], inputs)
    assert res.eq(mkint(-43))


def test_numerics_bor():
    inputs = [mkint(12), mkint(10)]
    res = builtin.numerics_bor([], inputs)
    assert res.eq(mkint(14))

    inputs = [mkint(42), mkint(0)]
    res = builtin.numerics_bor([], inputs)
    assert res.eq(mkint(42))

def test_numerics_pow2():
    v = mkint(12)
    res = builtin.numerics_pow2([], [v])
    assert res.eq(mkint(4096))

    v = mkint(0)
    res = builtin.numerics_pow2([], [v])
    assert res.eq(mkint(1))

    v = mkint(-1)
    with pytest.raises(builtin.P4BuiltinError):
        res = builtin.numerics_pow2([], [v])

def test_fresh():
    oldval = builtin.HOLDER.counter
    try:
        builtin.HOLDER.counter = 0 # scary global state
        res = builtin.fresh_fresh_tid([], [])
        assert res.value == 'FRESH__0'
    finally:
        builtin.HOLDER.counter = oldval


def textlist(*args):
    l = [mktext(arg) for arg in args]
    return objects.ListV.make(l, p4specast.TextT.INSTANCE.list_of())

def test_list_rev():
    arg = textlist()
    res = builtin.lists_rev_(None, [arg])
    assert res is arg

    arg = textlist('a')
    res = builtin.lists_rev_(None, [arg])
    assert res is arg

    arg = textlist('a', 'b')
    res = builtin.lists_rev_(None, [arg])
    exp = textlist('b', 'a')
    assert res.eq(exp)

def test_list_distinct():
    args = [textlist()]
    res = builtin.lists_distinct_(None, args)
    assert res.eq(objects.BoolV(True))

    args = [textlist('a')]
    res = builtin.lists_distinct_(None, args)
    assert res.eq(objects.BoolV(True))

    args = [textlist('a', 'a')]
    res = builtin.lists_distinct_(None, args)
    assert res.eq(objects.BoolV(False))

    args = [textlist('a', 'b', 'a')]
    res = builtin.lists_distinct_(None, args)
    assert res.eq(objects.BoolV(False))

def test_lists_concat():
    empty = textlist()
    args = [objects.ListV.make([empty, empty], p4specast.TextT.INSTANCE.list_of().list_of())]
    res = builtin.lists_concat_(None, args)
    assert res.eq(empty)
    assert repr(res.typ) == "p4specast.IterT(p4specast.TextT.INSTANCE, p4specast.List.INSTANCE)"

def test_list_assoc():
    # Create a simple association list of (text, text) pairs
    search_key = mktext('input_port')
    assoc_list = objects.ListV.make([
        objects.TupleV.make2(mktext('input_port'), mktext('32'), p4specast.TupleT([p4specast.TextT.INSTANCE, p4specast.TextT.INSTANCE])),
        objects.TupleV.make2(mktext('packet_length'), mktext('16'), p4specast.TupleT([p4specast.TextT.INSTANCE, p4specast.TextT.INSTANCE])),
        objects.TupleV.make2(mktext('output_port'), mktext('8'), p4specast.TupleT([p4specast.TextT.INSTANCE, p4specast.TextT.INSTANCE]))
    ], p4specast.TupleT([p4specast.TextT.INSTANCE, p4specast.TextT.INSTANCE]).list_of())

    input_values = [search_key, assoc_list]
    expected = p4specast.TextT.INSTANCE.opt_of().make_opt_value(mktext('32'))
    targs = [p4specast.TextT.INSTANCE, p4specast.TextT.INSTANCE]
    res = builtin.lists_assoc_(targs, input_values)
    assert res.eq(expected)

def make_set(*args):
    lst = []
    for el in args:
        value = mktext(el)
        lst.append(value)
    list_value = objects.ListV.make(lst, p4specast.TextT.INSTANCE.list_of())
    settyp = p4specast.VarT(builtin.set_id, [p4specast.TextT()])
    return objects.CaseV.make([list_value], builtin.map_mixop, settyp)


def test_union_set():
    # Union of two empty sets
    s1 = make_set()
    s2 = make_set()
    res = builtin.sets_union_set(None, [s1, s2])
    assert res.eq(make_set())

    # Union of empty and non-empty set
    s1 = make_set("a", "b")
    s2 = make_set()
    res = builtin.sets_union_set(None, [s1, s2])
    assert res.eq(make_set("a", "b"))
    res = builtin.sets_union_set(None, [s2, s1])
    assert res.eq(make_set("a", "b"))

    # Union of two identical sets
    s1 = make_set("x", "y")
    s2 = make_set("x", "y")
    res = builtin.sets_union_set(None, [s1, s2])
    assert res.eq(make_set("x", "y"))

    # Union of overlapping sets
    s1 = make_set("a", "b", "c")
    s2 = make_set("b", "c", "d")
    res = builtin.sets_union_set(None, [s1, s2])
    assert res.eq(make_set("a", "b", "c", "d"))

    # Union of disjoint sets
    s1 = make_set("m", "n")
    s2 = make_set("x", "y")
    res = builtin.sets_union_set(None, [s1, s2])
    assert res.eq(make_set("m", "n", "x", "y"))

    # Union of single element sets
    s1 = make_set("foo")
    s2 = make_set("bar")
    res = builtin.sets_union_set(None, [s1, s2])
    assert res.eq(make_set("foo", "bar"))

    # Union where one set is subset of the other
    s1 = make_set("a", "b", "c")
    s2 = make_set("b")
    res = builtin.sets_union_set(None, [s1, s2])
    assert res.eq(make_set("a", "b", "c"))
    res = builtin.sets_union_set(None, [s2, s1])
    assert builtin.sets_eq_set(None, [res, (make_set("a", "b", "c"))]).get_bool()

def test_unions_set():
    args = [objects.ListV.make([objects.CaseV.make([objects.ListV.make([], p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), []), p4specast.List()))], p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), [])])), objects.CaseV.make([objects.ListV.make([], p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), []), p4specast.List()))], p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), [])]))], p4specast.IterT(p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 21, 25)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), [])]), p4specast.List()))]
    res = builtin.sets_unions_set([p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), [])], args)
    exp = objects.CaseV.make([objects.ListV.make([], p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), []), p4specast.List()))], p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), [])]))
    assert res.eq(exp)

def test_diff_set():
    args = [objects.CaseV.make([objects.ListV.make([mktext('H')], p4specast.IterT(p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 116, 13, 14)), []), p4specast.List()))], p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 113, 36, 37)), [])])), objects.CaseV.make([objects.ListV.make([mktext('H')], p4specast.TextT.INSTANCE.list_of())], p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c6-runtime-type-wellformed.watsup', 373, 29, 32)), [])]))]
    res = builtin.sets_diff_set(None, args)
    exp = objects.CaseV.make([objects.ListV.make([], p4specast.IterT(p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 116, 13, 14)), []), p4specast.List()))], p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 113, 36, 37)), [])]))
    assert res.eq(exp)

def test_diff_set_2():
    # Difference with empty sets
    res = builtin.sets_diff_set(None, [make_set(), make_set()])
    assert res.eq(make_set())

    # Any set minus empty set equals the original set
    res = builtin.sets_diff_set(None, [make_set("a", "b"), make_set()])
    assert res.eq(make_set("a", "b"))

    # Empty set minus any set equals empty set
    res = builtin.sets_diff_set(None, [make_set(), make_set("a", "b")])
    assert res.eq(make_set())

    # Identical sets difference equals empty set
    res = builtin.sets_diff_set(None, [make_set("a", "b"), make_set("a", "b")])
    assert res.eq(make_set())

    # Partial overlap - remove common elements
    res = builtin.sets_diff_set(None, [make_set("a", "b", "c"), make_set("b", "c", "d")])
    assert res.eq(make_set("a"))

    # Disjoint sets - first set unchanged
    res = builtin.sets_diff_set(None, [make_set("a", "b"), make_set("c", "d")])
    assert res.eq(make_set("a", "b"))

    # Single element differences
    res = builtin.sets_diff_set(None, [make_set("x"), make_set("y")])
    assert res.eq(make_set("x"))

    # More complex case
    res = builtin.sets_diff_set(None, [make_set("a", "b", "c", "d", "e"), make_set("b", "d")])
    assert res.eq(make_set("a", "c", "e"))

def test_set_eq():
    res = builtin.sets_eq_set(None, [make_set(), make_set()])
    assert res.get_bool()
    res = builtin.sets_eq_set(None, [make_set("a"), make_set("a")])
    assert res.get_bool()
    res = builtin.sets_eq_set(None, [make_set("a"), make_set()])
    assert res.get_bool() == False
    res = builtin.sets_eq_set(None, [make_set("a"), make_set("b")])
    assert res.get_bool() == False

def test_intersect_set():
    # Intersection of empty sets
    res = builtin.sets_intersect_set(None, [make_set(), make_set()])
    assert res.eq(make_set())

    res = builtin.sets_intersect_set(None, [make_set("a"), make_set()])
    assert res.eq(make_set())

    res = builtin.sets_intersect_set(None, [make_set("a", "b"), make_set("a", "b")])
    assert res.eq(make_set("a", "b"))

    res = builtin.sets_intersect_set(None, [make_set("a", "b", "c"), make_set("b", "c", "d")])
    assert res.eq(make_set("b", "c"))

    res = builtin.sets_intersect_set(None, [make_set("a", "b"), make_set("c", "d")])
    assert res.eq(make_set())

def test_union_set_2():
    # Union of empty sets
    res = builtin.sets_union_set(None, [make_set(), make_set()])
    assert res.eq(make_set())

    # Union with empty set
    res = builtin.sets_union_set(None, [make_set("a"), make_set()])
    assert res.eq(make_set("a"))

    res = builtin.sets_union_set(None, [make_set(), make_set("b")])
    assert res.eq(make_set("b"))

    # Union of identical sets
    res = builtin.sets_union_set(None, [make_set("a", "b"), make_set("a", "b")])
    assert res.eq(make_set("a", "b"))

    # Union of overlapping sets
    res = builtin.sets_union_set(None, [make_set("a", "b", "c"), make_set("b", "c", "d")])
    assert res.eq(make_set("a", "b", "c", "d"))

    # Union of disjoint sets
    res = builtin.sets_union_set(None, [make_set("a", "b"), make_set("c", "d")])
    assert res.eq(make_set("a", "b", "c", "d"))

    # Union of single element sets
    res = builtin.sets_union_set(None, [make_set("x"), make_set("y")])
    assert res.eq(make_set("x", "y"))

def test_sub_set():
    res = builtin.sets_sub_set(None, [make_set(), make_set()])
    assert res.get_bool()
    res = builtin.sets_sub_set(None, [make_set(), make_set("a")])
    assert res.get_bool()

    res = builtin.sets_sub_set(None, [make_set("a", "b"), make_set("a", "b")])
    assert res.get_bool()

    res = builtin.sets_sub_set(None, [make_set("a"), make_set("a", "b")])
    assert res.get_bool()

    res = builtin.sets_sub_set(None, [make_set("a", "b"), make_set("a")])
    assert res.get_bool() == False
    res = builtin.sets_sub_set(None, [make_set("a", "b"), make_set("c", "d")])
    assert res.get_bool() == False


def make_map(*args):
    lst = []
    pairtyp = p4specast.VarT(p4specast.Id('pair', p4specast.NO_REGION), [p4specast.TextT(), p4specast.TextT()])
    for key, value in args:
        key_value = mktext(key)
        value_value = mktext(value)
        arrow = objects.CaseV.make([key_value, value_value], builtin.arrow_mixop, pairtyp)
        lst.append(arrow)
    list_value = objects.ListV.make(lst, pairtyp.list_of())
    maptyp = p4specast.VarT(builtin.map_id, [p4specast.TextT(), p4specast.TextT()])
    return objects.CaseV.make([list_value], builtin.map_mixop, maptyp)


def test_add_map():
    map_value = make_map()
    res = builtin.maps_add_map([p4specast.TextT(), p4specast.TextT()],
                               [map_value, mktext("C"),
                                mktext("d1")])
    assert res.eq(make_map(("C", "d1")))

    map_value = make_map(("A", "b1"), ("B", "c1"))
    res = builtin.maps_add_map([p4specast.TextT(), p4specast.TextT()],
                               [map_value, mktext("C"),
                                mktext("d1")])
    assert res.eq(make_map(("A", "b1"), ("B", "c1"), ("C", "d1")))


    map_value = make_map(("A", "b1"), ("C", "c1"))
    res = builtin.maps_add_map([p4specast.TextT(), p4specast.TextT()],
                               [map_value, mktext("C"),
                                mktext("d1")])
    assert res.eq(make_map(("A", "b1"), ("C", "d1")))

    map_value = make_map(("A", "b1"), ("D", "c1"))
    res = builtin.maps_add_map([p4specast.TextT(), p4specast.TextT()],
                               [map_value, mktext("C"),
                                mktext("d1")])
    assert res.eq(make_map(("A", "b1"), ("C", "d1"), ("D", "c1")))


def test_find_maps():
    map_value1 = make_map(("A", "a1"), ("B", "b"))
    map_value2 = make_map(("A", "a2"), ("C", "x"))
    lst_value = objects.ListV.make([map_value1, map_value2], map_value1.typ.list_of())

    res = builtin.maps_find_maps([p4specast.TextT(), p4specast.TextT()],
                                 [lst_value, mktext("C")])
    assert res.get_opt_value().eq(mktext("x"))
    res = builtin.maps_find_maps([p4specast.TextT(), p4specast.TextT()],
                                 [lst_value, mktext("A")])
    assert res.get_opt_value().eq(mktext("a1"))
    res = builtin.maps_find_maps([p4specast.TextT(), p4specast.TextT()],
                                 [lst_value, mktext("D")])
    assert res.get_opt_value() is None

def test_lists_partition():
    # Test partitioning an empty list
    empty_list = textlist()
    len_val = objects.NumV.fromstr('0', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    res = builtin.lists_partition_([p4specast.TextT.INSTANCE], [empty_list, len_val])
    assert isinstance(res, objects.TupleV)
    assert res._get_size_list() == 2
    assert res._get_list(0).eq(empty_list)
    assert res._get_list(1).eq(empty_list)

    # Test partitioning at index 0 (all elements go to right)
    test_list = textlist("a", "b", "c")
    len_val = objects.NumV.fromstr('0', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    res = builtin.lists_partition_([p4specast.TextT()], [test_list, len_val])
    assert isinstance(res, objects.TupleV)
    assert res._get_size_list() == 2
    left_list, right_list = res._get_list(0), res._get_list(1)
    assert left_list.eq(textlist())  # empty
    assert right_list.eq(test_list)  # all elements

    # Test partitioning at index 2 (first 2 elements go to left, rest to right)
    test_list = textlist("a", "b", "c", "d")
    len_val = objects.NumV.fromstr('2', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    res = builtin.lists_partition_([p4specast.TextT()], [test_list, len_val])
    assert isinstance(res, objects.TupleV)
    assert res._get_size_list() == 2
    left_list, right_list = res._get_list(0), res._get_list(1)
    assert left_list.eq(textlist("a", "b"))
    assert right_list.eq(textlist("c", "d"))

    # Test partitioning with length >= list length (all elements go to left)
    test_list = textlist("x", "y")
    len_val = objects.NumV.fromstr('5', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    res = builtin.lists_partition_([p4specast.TextT()], [test_list, len_val])
    assert isinstance(res, objects.TupleV)
    assert res._get_size_list() == 2
    left_list, right_list = res._get_list(0), res._get_list(1)
    assert left_list.eq(test_list)  # all elements
    assert right_list.eq(textlist())  # empty

def make_text(s):
    return mktext(s)

def make_nat_list(*values):
    nat_values = []
    for val in values:
        nat_values.append(objects.NumV.fromstr(str(val), p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT))
    return objects.ListV.make(nat_values, p4specast.NumT.NAT.list_of())

def test_texts_strip_suffix():
    res = builtin.texts_strip_suffix([], [make_text('action_list(t)'), make_text(')')])
    assert res.eq(make_text('action_list(t'))

    res = builtin.texts_strip_suffix([], [make_text('hello_world'), make_text('_world')])
    assert res.eq(make_text('hello'))

    res = builtin.texts_strip_suffix([], [make_text('test'), make_text('')])
    assert res.eq(make_text('test'))

    res = builtin.texts_strip_suffix([], [make_text('abc'), make_text('abc')])
    assert res.eq(make_text(''))

def test_texts_strip_prefix():
    res = builtin.texts_strip_prefix([], [make_text('hello_world'), make_text('hello_')])
    assert res.eq(make_text('world'))

    res = builtin.texts_strip_prefix([], [make_text('test'), make_text('')])
    assert res.eq(make_text('test'))

    res = builtin.texts_strip_prefix([], [make_text('abc'), make_text('abc')])
    assert res.eq(make_text(''))

def test_nats_sum():
    res = builtin.nats_sum([], [make_nat_list()])
    expected = objects.NumV.fromstr('0', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_sum([], [make_nat_list(42)])
    expected = objects.NumV.fromstr('42', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_sum([], [make_nat_list(1, 2, 3, 4, 5)])
    expected = objects.NumV.fromstr('15', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_sum([], [make_nat_list(1000000, 2000000, 3000000)])
    expected = objects.NumV.fromstr('6000000', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

def test_nats_max():
    res = builtin.nats_max([], [make_nat_list(42)])
    expected = objects.NumV.fromstr('42', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_max([], [make_nat_list(1, 5, 3, 2, 4)])
    expected = objects.NumV.fromstr('5', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_max([], [make_nat_list(7, 3, 7, 1, 7)])
    expected = objects.NumV.fromstr('7', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_max([], [make_nat_list(1000000, 5000000, 2000000)])
    expected = objects.NumV.fromstr('5000000', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    with pytest.raises(builtin.P4BuiltinError):
        builtin.nats_max([], [make_nat_list()])

def test_nats_min():
    res = builtin.nats_min([], [make_nat_list(42)])
    expected = objects.NumV.fromstr('42', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_min([], [make_nat_list(5, 1, 3, 2, 4)])
    expected = objects.NumV.fromstr('1', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_min([], [make_nat_list(7, 2, 5, 2, 9)])
    expected = objects.NumV.fromstr('2', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    res = builtin.nats_min([], [make_nat_list(5000000, 1000000, 2000000)])
    expected = objects.NumV.fromstr('1000000', p4specast.NatT.INSTANCE, typ=p4specast.NumT.NAT)
    assert res.eq(expected)

    with pytest.raises(builtin.P4BuiltinError):
        builtin.nats_min([], [make_nat_list()])

def test_unions_set_2():
    # Union of empty list of sets
    res = builtin.sets_unions_set([p4specast.TextT.INSTANCE], [objects.ListV.make0(p4specast.TextT.INSTANCE.list_of())])
    assert res.eq(make_set())
    # Union of single set
    res = builtin.sets_unions_set([p4specast.TextT.INSTANCE], [objects.ListV.make1(make_set("a"), p4specast.TextT.INSTANCE.list_of())])
    assert res.eq(make_set("a"))
    # Union of two empty sets
    res = builtin.sets_unions_set([p4specast.TextT.INSTANCE], [objects.ListV.make2(make_set(), make_set(), p4specast.TextT.INSTANCE.list_of())])
    assert res.eq(make_set())
    # Union of two disjoint sets
    res = builtin.sets_unions_set([p4specast.TextT.INSTANCE], [objects.ListV.make2(make_set("a"), make_set("b"), p4specast.TextT.INSTANCE.list_of())])
    assert res.eq(make_set("b", "a"))
    # Union of three overlapping sets
    res = builtin.sets_unions_set([p4specast.TextT.INSTANCE], [objects.ListV.make([make_set("a", "b"), make_set("b", "c"), make_set("c", "d")], p4specast.TextT.INSTANCE.list_of())])
    assert res.eq(make_set("a", "b", "c", "d"))
    # Union of identical sets
    res = builtin.sets_unions_set([p4specast.TextT.INSTANCE], [objects.ListV.make2(make_set("x", "y"), make_set("x", "y"), p4specast.TextT.INSTANCE.list_of())])
    assert res.eq(make_set("x", "y"))

# ________________________________________________________________
# Property-based tests for set operations using Hypothesis

from hypothesis import given, strategies as st

def set_to_python(set_value):
    """Convert a P4 set value to a Python frozenset for comparison."""
    elems = builtin._extract_set_elems(set_value)
    return frozenset(elem.get_text() for elem in elems)

@st.composite
def text_set_strategy(draw):
    """Strategy to generate P4 sets containing text values."""
    elements = draw(st.lists(st.text(alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=1, max_size=3), min_size=0, max_size=10))
    elements = [val.encode('utf-8') for val in elements]
    # Remove duplicates to create a proper set
    unique_elements = list(dict.fromkeys(elements))
    return make_set(*unique_elements)

# Union properties
@given(s1=text_set_strategy(), s2=text_set_strategy())
def test_union_commutative(s1, s2):
    """Union is commutative: A ∪ B = B ∪ A"""
    res1 = builtin.sets_union_set(None, [s1, s2])
    res2 = builtin.sets_union_set(None, [s2, s1])
    assert builtin.sets_eq_set(None, [res1, res2]).get_bool()

@given(s1=text_set_strategy(), s2=text_set_strategy(), s3=text_set_strategy())
def test_union_associative(s1, s2, s3):
    """Union is associative: (A ∪ B) ∪ C = A ∪ (B ∪ C)"""
    left = builtin.sets_union_set(None, [builtin.sets_union_set(None, [s1, s2]), s3])
    right = builtin.sets_union_set(None, [s1, builtin.sets_union_set(None, [s2, s3])])
    assert builtin.sets_eq_set(None, [left, right]).get_bool()

@given(s=text_set_strategy())
def test_union_identity(s):
    """Empty set is identity for union: A ∪ ∅ = A"""
    empty = make_set()
    res = builtin.sets_union_set(None, [s, empty])
    assert builtin.sets_eq_set(None, [res, s]).get_bool()

@given(s=text_set_strategy())
def test_union_idempotent(s):
    """Union is idempotent: A ∪ A = A"""
    res = builtin.sets_union_set(None, [s, s])
    assert builtin.sets_eq_set(None, [res, s]).get_bool()

# Intersection properties
@given(s1=text_set_strategy(), s2=text_set_strategy())
def test_intersect_commutative(s1, s2):
    """Intersection is commutative: A ∩ B = B ∩ A"""
    res1 = builtin.sets_intersect_set(None, [s1, s2])
    res2 = builtin.sets_intersect_set(None, [s2, s1])
    assert builtin.sets_eq_set(None, [res1, res2]).get_bool()

@given(s1=text_set_strategy(), s2=text_set_strategy(), s3=text_set_strategy())
def test_intersect_associative(s1, s2, s3):
    """Intersection is associative: (A ∩ B) ∩ C = A ∩ (B ∩ C)"""
    left = builtin.sets_intersect_set(None, [builtin.sets_intersect_set(None, [s1, s2]), s3])
    right = builtin.sets_intersect_set(None, [s1, builtin.sets_intersect_set(None, [s2, s3])])
    assert builtin.sets_eq_set(None, [left, right]).get_bool()

@given(s=text_set_strategy())
def test_intersect_empty(s):
    """Intersection with empty set is empty: A ∩ ∅ = ∅"""
    empty = make_set()
    res = builtin.sets_intersect_set(None, [s, empty])
    assert builtin.sets_eq_set(None, [res, empty]).get_bool()

@given(s=text_set_strategy())
def test_intersect_idempotent(s):
    """Intersection is idempotent: A ∩ A = A"""
    res = builtin.sets_intersect_set(None, [s, s])
    assert builtin.sets_eq_set(None, [res, s]).get_bool()

# Difference properties
@given(s=text_set_strategy())
def test_diff_self_empty(s):
    """A - A = ∅"""
    res = builtin.sets_diff_set(None, [s, s])
    assert builtin.sets_eq_set(None, [res, make_set()]).get_bool()

@given(s=text_set_strategy())
def test_diff_empty_identity(s):
    """A - ∅ = A"""
    empty = make_set()
    res = builtin.sets_diff_set(None, [s, empty])
    assert builtin.sets_eq_set(None, [res, s]).get_bool()

@given(s=text_set_strategy())
def test_empty_diff_empty(s):
    """∅ - A = ∅"""
    empty = make_set()
    res = builtin.sets_diff_set(None, [empty, s])
    assert builtin.sets_eq_set(None, [res, empty]).get_bool()

# Subset properties
@given(s=text_set_strategy())
def test_subset_reflexive(s):
    """Every set is a subset of itself: A ⊆ A"""
    res = builtin.sets_sub_set(None, [s, s])
    assert res.get_bool()

@given(s=text_set_strategy())
def test_empty_subset_all(s):
    """Empty set is a subset of any set: ∅ ⊆ A"""
    empty = make_set()
    res = builtin.sets_sub_set(None, [empty, s])
    assert res.get_bool()

@given(s1=text_set_strategy(), s2=text_set_strategy(), s3=text_set_strategy())
def test_subset_transitive(s1, s2, s3):
    """Subset is transitive: if A ⊆ B and B ⊆ C then A ⊆ C"""
    if builtin.sets_sub_set(None, [s1, s2]).get_bool() and builtin.sets_sub_set(None, [s2, s3]).get_bool():
        assert builtin.sets_sub_set(None, [s1, s3]).get_bool()

@given(s1=text_set_strategy(), s2=text_set_strategy())
def test_subset_antisymmetric(s1, s2):
    """If A ⊆ B and B ⊆ A then A = B"""
    if builtin.sets_sub_set(None, [s1, s2]).get_bool() and builtin.sets_sub_set(None, [s2, s1]).get_bool():
        assert builtin.sets_eq_set(None, [s1, s2]).get_bool()

# Equality properties
@given(s=text_set_strategy())
def test_eq_reflexive(s):
    """Equality is reflexive: A = A"""
    res = builtin.sets_eq_set(None, [s, s])
    assert res.get_bool()

@given(s1=text_set_strategy(), s2=text_set_strategy())
def test_eq_symmetric(s1, s2):
    """Equality is symmetric: if A = B then B = A"""
    res1 = builtin.sets_eq_set(None, [s1, s2])
    res2 = builtin.sets_eq_set(None, [s2, s1])
    assert res1.get_bool() == res2.get_bool()

@given(s1=text_set_strategy(), s2=text_set_strategy(), s3=text_set_strategy())
def test_eq_transitive(s1, s2, s3):
    """Equality is transitive: if A = B and B = C then A = C"""
    if builtin.sets_eq_set(None, [s1, s2]).get_bool() and builtin.sets_eq_set(None, [s2, s3]).get_bool():
        assert builtin.sets_eq_set(None, [s1, s3]).get_bool()

# Cross-operation properties
@given(s1=text_set_strategy(), s2=text_set_strategy(), s3=text_set_strategy())
def test_union_intersection_distributive(s1, s2, s3):
    """Union distributes over intersection: A ∪ (B ∩ C) = (A ∪ B) ∩ (A ∪ C)"""
    left = builtin.sets_union_set(None, [s1, builtin.sets_intersect_set(None, [s2, s3])])
    right = builtin.sets_intersect_set(None, [builtin.sets_union_set(None, [s1, s2]), builtin.sets_union_set(None, [s1, s3])])
    assert builtin.sets_eq_set(None, [left, right]).get_bool()

@given(s1=text_set_strategy(), s2=text_set_strategy())
def test_diff_union_relationship(s1, s2):
    """A - B and A ∩ B are disjoint, and their union is A (assuming B ⊆ A or general case)"""
    diff = builtin.sets_diff_set(None, [s1, s2])
    intersect = builtin.sets_intersect_set(None, [s1, s2])
    union_result = builtin.sets_union_set(None, [diff, intersect])
    # This should equal s1
    assert builtin.sets_eq_set(None, [union_result, s1]).get_bool()

@given(s1=text_set_strategy(), s2=text_set_strategy())
def test_subset_via_union(s1, s2):
    """A ⊆ B iff A ∪ B = B"""
    subset_res = builtin.sets_sub_set(None, [s1, s2])
    union_res = builtin.sets_union_set(None, [s1, s2])
    union_eq = builtin.sets_eq_set(None, [union_res, s2])
    assert subset_res.get_bool() == union_eq.get_bool()

@given(s1=text_set_strategy(), s2=text_set_strategy())
def test_subset_via_intersection(s1, s2):
    """A ⊆ B iff A ∩ B = A"""
    subset_res = builtin.sets_sub_set(None, [s1, s2])
    intersect_res = builtin.sets_intersect_set(None, [s1, s2])
    intersect_eq = builtin.sets_eq_set(None, [intersect_res, s1])
    assert subset_res.get_bool() == intersect_eq.get_bool()

# unions_set (multiple sets) properties
@given(sets=st.lists(text_set_strategy(), min_size=0, max_size=5))
def test_unions_set_consistency(sets):
    """unions_set should produce the same result as repeatedly calling union_set"""
    # Use the same type pattern as existing tests
    list_typ = p4specast.TextT.INSTANCE.list_of()

    if not sets:
        # Empty list case
        list_value = objects.ListV.make0(list_typ)
        res = builtin.sets_unions_set([p4specast.TextT.INSTANCE], [list_value])
        assert builtin.sets_eq_set(None, [res, make_set()]).get_bool()
    elif len(sets) == 1:
        # Single set case
        list_value = objects.ListV.make([sets[0]], list_typ)
        res = builtin.sets_unions_set([p4specast.TextT.INSTANCE], [list_value])
        assert builtin.sets_eq_set(None, [res, sets[0]]).get_bool()
    else:
        # Multiple sets case - compare with iterative union
        list_value = objects.ListV.make(sets, list_typ)
        res_unions = builtin.sets_unions_set([p4specast.TextT.INSTANCE], [list_value])

        # Build result iteratively
        res_iterative = sets[0]
        for s in sets[1:]:
            res_iterative = builtin.sets_union_set(None, [res_iterative, s])

        assert builtin.sets_eq_set(None, [res_unions, res_iterative]).get_bool()

# ________________________________________________________________
# Stateful property-based testing

from hypothesis.stateful import RuleBasedStateMachine, rule, invariant, Bundle

class SetStateMachine(RuleBasedStateMachine):
    """Stateful test that compares P4 set operations against Python frozenset model."""

    sets = Bundle('sets')

    def __init__(self):
        super(SetStateMachine, self).__init__()
        # Map from set names to (p4_set, frozenset_model)
        self.set_store = {}

    @rule(target=sets, elements=st.lists(st.text(alphabet=st.characters(min_codepoint=97, max_codepoint=122), min_size=1, max_size=3), max_size=8))
    def create_set(self, elements):
        """Create a new set from a list of elements."""
        # Encode elements for Python 2 compatibility
        elements = [val.encode('utf-8') for val in elements]
        unique_elements = list(dict.fromkeys(elements))

        # Create P4 set
        p4_set = make_set(*unique_elements)

        # Create model frozenset
        model_set = frozenset(unique_elements)

        # Generate a unique name
        name = 'set_%d' % len(self.set_store)
        self.set_store[name] = (p4_set, model_set)
        return name

    @rule(target=sets, s1=sets, s2=sets)
    def union_sets(self, s1, s2):
        """Compute union of two sets."""
        p4_s1, model_s1 = self.set_store[s1]
        p4_s2, model_s2 = self.set_store[s2]

        # P4 union
        p4_result = builtin.sets_union_set(None, [p4_s1, p4_s2])

        # Model union
        model_result = model_s1 | model_s2

        # Store result
        name = 'union_%s_%s' % (s1, s2)
        self.set_store[name] = (p4_result, model_result)
        return name

    @rule(target=sets, s1=sets, s2=sets)
    def intersect_sets(self, s1, s2):
        """Compute intersection of two sets."""
        p4_s1, model_s1 = self.set_store[s1]
        p4_s2, model_s2 = self.set_store[s2]

        # P4 intersection
        p4_result = builtin.sets_intersect_set(None, [p4_s1, p4_s2])

        # Model intersection
        model_result = model_s1 & model_s2

        # Store result
        name = 'intersect_%s_%s' % (s1, s2)
        self.set_store[name] = (p4_result, model_result)
        return name

    @rule(target=sets, s1=sets, s2=sets)
    def diff_sets(self, s1, s2):
        """Compute difference of two sets."""
        p4_s1, model_s1 = self.set_store[s1]
        p4_s2, model_s2 = self.set_store[s2]

        # P4 difference
        p4_result = builtin.sets_diff_set(None, [p4_s1, p4_s2])

        # Model difference
        model_result = model_s1 - model_s2

        # Store result
        name = 'diff_%s_%s' % (s1, s2)
        self.set_store[name] = (p4_result, model_result)
        return name

    @rule(s1=sets, s2=sets)
    def check_subset(self, s1, s2):
        """Check if s1 is a subset of s2."""
        p4_s1, model_s1 = self.set_store[s1]
        p4_s2, model_s2 = self.set_store[s2]

        # P4 subset check
        p4_result = builtin.sets_sub_set(None, [p4_s1, p4_s2]).get_bool()

        # Model subset check
        model_result = model_s1 <= model_s2

        assert p4_result == model_result, "Subset check mismatch: P4=%s, Model=%s" % (p4_result, model_result)

    @rule(s1=sets, s2=sets)
    def check_equality(self, s1, s2):
        """Check if two sets are equal."""
        p4_s1, model_s1 = self.set_store[s1]
        p4_s2, model_s2 = self.set_store[s2]

        # P4 equality check
        p4_result = builtin.sets_eq_set(None, [p4_s1, p4_s2]).get_bool()

        # Model equality check
        model_result = (model_s1 == model_s2)

        assert p4_result == model_result, "Equality check mismatch: P4=%s, Model=%s" % (p4_result, model_result)

    @invariant()
    def sets_match_model(self):
        """Invariant: all P4 sets match their frozenset models."""
        for name, (p4_set, model_set) in self.set_store.items():
            # Convert P4 set to Python set
            p4_elements = set_to_python(p4_set)

            # Check they match
            assert p4_elements == model_set, "Set mismatch for %s: P4=%s, Model=%s" % (name, p4_elements, model_set)

TestSetOperations = SetStateMachine.TestCase
