from rpyp4sp import p4specast, objects, builtin, context, integers

def test_list_rev():
    arg = objects.ListV([], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('dir', p4specast.Region.line_span('spec/1a-syntax-el.watsup', 90, 7, 10)), []), p4specast.List()))
    res = builtin.lists_rev_(None, 'rev_', None, [arg])
    assert res is arg

    arg = objects.ListV([objects.CaseV(p4specast.MixOp([[p4specast.AtomT('INOUT')]]), [], 13, p4specast.VarT(p4specast.Id('dir', p4specast.NO_REGION), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('NO')]]), [], 21, p4specast.VarT(p4specast.Id('dir', p4specast.NO_REGION), []))], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('dir', p4specast.Region.line_span('spec/1a-syntax-el.watsup', 90, 7, 10)), []), p4specast.List()))
    res = builtin.lists_rev_(None, 'rev_', None, [arg])
    exp = objects.ListV([objects.CaseV(p4specast.MixOp([[p4specast.AtomT('NO')]]), [], 21, p4specast.VarT(p4specast.Id('dir', p4specast.NO_REGION), [])), objects.CaseV(p4specast.MixOp([[p4specast.AtomT('INOUT')]]), [], 13, p4specast.VarT(p4specast.Id('dir', p4specast.NO_REGION), []))], -1, p4specast.IterT(p4specast.VarT(p4specast.Id('dir', p4specast.Region.line_span('spec/1a-syntax-el.watsup', 90, 7, 10)), []), p4specast.List()))
    assert res.eq(exp)

def test_list_distinct():
    args = [objects.ListV([], -1, p4specast.IterT(p4specast.TextT(), p4specast.List()))]
    res = builtin.lists_distinct_(None, 'distinct_', None, args)
    assert res.eq(objects.BoolV(True))

    args = [objects.ListV([objects.TextV('Set_dmac', 14, p4specast.TextT()), objects.TextV('drop', 18, p4specast.TextT())], -1, p4specast.IterT(p4specast.TextT(), p4specast.List()))]
    res = builtin.lists_distinct_(None, 'distinct_', None, args)
    assert res.eq(objects.BoolV(True))

    args = [objects.ListV([objects.TextV('Set_dmac', 14, p4specast.TextT()), objects.TextV('Set_dmac', 18, p4specast.TextT())], -1, p4specast.IterT(p4specast.TextT(), p4specast.List()))]
    res = builtin.lists_distinct_(None, 'distinct_', None, args)
    assert res.eq(objects.BoolV(False))
