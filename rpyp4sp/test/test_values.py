from rpyp4sp import p4specast, objects, interp, rpyjson


def test_compare_casev():
    self = objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), [], 100, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), []))
    other = objects.CaseV(p4specast.MixOp([[p4specast.AtomT('IntT', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 36, 4), p4specast.Position('spec/2c1-runtime-type.watsup', 36, 8)))]]), [], 111, p4specast.VarT(p4specast.Id('numtyp', p4specast.Region(p4specast.Position('spec/2c1-runtime-type.watsup', 35, 7), p4specast.Position('spec/2c1-runtime-type.watsup', 35, 13))), []))
    res = self.compare(other)
    assert res == 0