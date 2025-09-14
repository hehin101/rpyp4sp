from rpyp4sp import p4specast, objects, builtin, context, integers

def test_int_to_text():
    res = builtin.texts_int_to_text(None, 'int_to_text', [], [objects.NumV.fromstr('1234', 'Int', typ=p4specast.NumT(p4specast.IntT()))])
    assert res.eq(objects.TextV('1234'))

def mkint(val):
    return objects.NumV.fromstr(str(val), 'Int', typ=p4specast.NumT(p4specast.IntT()))

def test_shl():
    res = builtin.numerics_shl(None, 'shl', [], [mkint(1234), mkint(4)])
    assert res.eq(mkint(1234 << 4))

def test_fresh():
    oldval = builtin.HOLDER.counter
    try:
        builtin.HOLDER.counter = 0 # scary global state
        res = builtin.fresh_fresh_tid(None, 'fresh_tid', [], [])
        assert res.value == 'FRESH__0'
    finally:
        builtin.HOLDER.counter = oldval


def textlist(*args):
    l = [objects.TextV(arg, typ=p4specast.TextT()) for arg in args]
    return objects.ListV(l, typ=p4specast.IterT(p4specast.TextT(), p4specast.List()))

def test_list_rev():
    arg = textlist()
    res = builtin.lists_rev_(None, 'rev_', None, [arg])
    assert res is arg

    arg = textlist('a')
    res = builtin.lists_rev_(None, 'rev_', None, [arg])
    assert res is arg

    arg = textlist('a', 'b')
    res = builtin.lists_rev_(None, 'rev_', None, [arg])
    exp = textlist('b', 'a')
    assert res.eq(exp)

def test_list_distinct():
    args = [textlist()]
    res = builtin.lists_distinct_(None, 'distinct_', None, args)
    assert res.eq(objects.BoolV(True))

    args = [textlist('a')]
    res = builtin.lists_distinct_(None, 'distinct_', None, args)
    assert res.eq(objects.BoolV(True))

    args = [textlist('a', 'a')]
    res = builtin.lists_distinct_(None, 'distinct_', None, args)
    assert res.eq(objects.BoolV(False))

    args = [textlist('a', 'b', 'a')]
    res = builtin.lists_distinct_(None, 'distinct_', None, args)
    assert res.eq(objects.BoolV(False))

def test_lists_concat():
    empty = objects.ListV([], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2a-runtime-domain.watsup', 10, 7, 10)), []), p4specast.List()))
    args = [objects.ListV([empty, empty], -1, p4specast.IterT(p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2a-runtime-domain.watsup', 10, 7, 10)), []), p4specast.List()), p4specast.List()))]
    res = builtin.lists_concat_(None, 'distinct_', None, args)
    assert res.eq(empty)
    assert repr(res.typ) == "p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2a-runtime-domain.watsup', 10, 7, 10)), []), p4specast.List())"

def make_set(*args):
    lst = []
    for el in args:
        value = objects.TextV(el, typ=p4specast.TextT())
        lst.append(value)
    list_value = objects.ListV(lst, typ=p4specast.IterT(p4specast.TextT(), p4specast.List()))
    settyp = p4specast.VarT(builtin.set_id, [p4specast.TextT()])
    return objects.CaseV(builtin.map_mixop, [list_value], typ=settyp)


def test_union_set():
    args = [objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([], 6524, p4specast.IterT(p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 73, 24, 25)), []), p4specast.List()))], 6525, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 73, 24, 25)), [])])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('tparam', p4specast.Region.line_span('spec/1a-syntax-el.watsup', 123, 7, 13)), []), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c6-runtime-type-wellformed.watsup', 526, 29, 32)), [])]))]
    res = builtin.sets_union_set(None, 'union_set', None, args)
    assert res.eq(args[0])
    
    args = [objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([objects.TextV('H', 264, p4specast.VarT(p4specast.Id('tparam', p4specast.NO_REGION), []))], 11709, p4specast.IterT(p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 116, 13, 14)), []), p4specast.List()))], 11710, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 113, 36, 37)), [])])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([objects.TextV('H', 264, p4specast.VarT(p4specast.Id('tparam', p4specast.NO_REGION), []))], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('tparam', p4specast.Region.line_span('spec/1a-syntax-el.watsup', 123, 7, 13)), []), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c6-runtime-type-wellformed.watsup', 373, 29, 32)), [])]))]
    res = builtin.sets_union_set(None, 'union_set', None, args)
    exp = objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([objects.TextV('H', 264, p4specast.VarT(p4specast.Id('tparam', p4specast.NO_REGION), []))], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 116, 13, 14)), []), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 113, 36, 37)), [])]))
    assert res.eq(exp)
    
def test_unions_set():
    args = [objects.ListV([objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), []), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), [])])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), []), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), [])]))], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 21, 25)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), [])]), p4specast.List()))]
    res = builtin.sets_unions_set(None, 'unions_set', [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), [])], args)
    exp = objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), []), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c3-runtime-type-subst.watsup', 7, 25, 28)), [])]))
    assert res.eq(exp)

def test_diff_set():
    args = [objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([objects.TextV('H', 264, p4specast.TextT())], 11709, p4specast.IterT(p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 116, 13, 14)), []), p4specast.List()))], 11710, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 113, 36, 37)), [])])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([objects.TextV('H', 264, p4specast.TextT())], -1, p4specast.IterT(p4specast.TextT(), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('tid', p4specast.Region.line_span('spec/2c6-runtime-type-wellformed.watsup', 373, 29, 32)), [])]))]
    res = builtin.sets_diff_set(None, 'diff_set', None, args)
    exp = objects.CaseV(p4specast.MixOp([[p4specast.AtomT.line_span('{', 'spec/0-aux.watsup', 71, 17, 18)], [p4specast.AtomT.line_span('}', 'spec/0-aux.watsup', 71, 22, 23)]]), [objects.ListV([], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 116, 13, 14)), []), p4specast.List()))], -1, p4specast.VarT(p4specast.Id('set', p4specast.Region.line_span('spec/0-aux.watsup', 71, 7, 11)), [p4specast.VarT(p4specast.Id('K', p4specast.Region.line_span('spec/0-aux.watsup', 113, 36, 37)), [])]))
    assert res.eq(exp)

def test_set_eq():
    res = builtin.sets_eq_set(None, 'diff_set', None, [make_set(), make_set()])
    assert res.get_bool()
    res = builtin.sets_eq_set(None, 'diff_set', None, [make_set("a"), make_set("a")])
    assert res.get_bool()
    res = builtin.sets_eq_set(None, 'diff_set', None, [make_set("a"), make_set()])
    assert res.get_bool() == False
    res = builtin.sets_eq_set(None, 'diff_set', None, [make_set("a"), make_set("b")])
    assert res.get_bool() == False
    

def make_map(*args):
    lst = []
    pairtyp = p4specast.VarT(p4specast.Id('pair', p4specast.NO_REGION), [p4specast.TextT(), p4specast.TextT()])
    for key, value in args:
        key_value = objects.TextV(key, typ=p4specast.TextT())
        value_value = objects.TextV(value, typ=p4specast.TextT())
        arrow = objects.CaseV(builtin.arrow_mixop, [key_value, value_value], typ=pairtyp)
        lst.append(arrow)
    list_value = objects.ListV(lst, typ=p4specast.IterT(pairtyp, p4specast.List()))
    maptyp = p4specast.VarT(builtin.map_id, [p4specast.TextT(), p4specast.TextT()])
    return objects.CaseV(builtin.map_mixop, [list_value], typ=maptyp)


def test_add_map():
    map_value = make_map()
    res = builtin.maps_add_map(None, "add_map", [p4specast.TextT(), p4specast.TextT()],
                               [map_value, objects.TextV("C", typ=p4specast.TextT()),
                                objects.TextV("d1", typ=p4specast.TextT())])
    assert res.eq(make_map(("C", "d1")))

    map_value = make_map(("A", "b1"), ("B", "c1"))
    res = builtin.maps_add_map(None, "add_map", [p4specast.TextT(), p4specast.TextT()],
                               [map_value, objects.TextV("C", typ=p4specast.TextT()),
                                objects.TextV("d1", typ=p4specast.TextT())])
    assert res.eq(make_map(("A", "b1"), ("B", "c1"), ("C", "d1")))


    map_value = make_map(("A", "b1"), ("C", "c1"))
    res = builtin.maps_add_map(None, "add_map", [p4specast.TextT(), p4specast.TextT()],
                               [map_value, objects.TextV("C", typ=p4specast.TextT()),
                                objects.TextV("d1", typ=p4specast.TextT())])
    assert res.eq(make_map(("A", "b1"), ("C", "d1")))

    map_value = make_map(("A", "b1"), ("D", "c1"))
    res = builtin.maps_add_map(None, "add_map", [p4specast.TextT(), p4specast.TextT()],
                               [map_value, objects.TextV("C", typ=p4specast.TextT()),
                                objects.TextV("d1", typ=p4specast.TextT())])
    assert res.eq(make_map(("A", "b1"), ("C", "d1"), ("D", "c1")))


def test_find_maps():
    map_value1 = make_map(("A", "a1"), ("B", "b"))
    map_value2 = make_map(("A", "a2"), ("C", "x"))
    lst_value = objects.ListV([map_value1, map_value2], typ=p4specast.IterT(map_value1.typ, p4specast.List()))

    res = builtin.maps_find_maps(None, "find_maps", [p4specast.TextT(), p4specast.TextT()],
                                 [lst_value, objects.TextV("C", typ=p4specast.TextT())])
    assert res.value.eq(objects.TextV("x", typ=p4specast.TextT()))
    res = builtin.maps_find_maps(None, "find_maps", [p4specast.TextT(), p4specast.TextT()],
                                 [lst_value, objects.TextV("A", typ=p4specast.TextT())])
    assert res.value.eq(objects.TextV("a1", typ=p4specast.TextT()))
    res = builtin.maps_find_maps(None, "find_maps", [p4specast.TextT(), p4specast.TextT()],
                                 [lst_value, objects.TextV("D", typ=p4specast.TextT())])
    assert res.value is None
