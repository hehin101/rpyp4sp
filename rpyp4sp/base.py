class SubBase(object):
    _attrs_ = []

class BaseV(SubBase):
    _attrs_ = []
    @staticmethod
    def fromjson(value):
        from rpyp4sp import p4specast, objects
        from rpyp4sp.error import P4UnknownTypeError
        typ = p4specast.Type.fromjson(value.get_dict_value('note').get_dict_value('typ'))
        content = value.get_dict_value('it')
        what = content.get_list_item(0).value_string()
        if what == 'BoolV':
            value = objects.BoolV.fromjson(content, typ)
        elif what == 'NumV':
            value = objects.NumV.fromjson(content, typ)
        elif what == 'TextV':
            value = objects.TextV.fromjson(content, typ)
        elif what == 'StructV':
            value = objects.StructV.fromjson(content, typ)
        elif what == 'CaseV':
            value = objects.CaseV.fromjson(content, typ)
        elif what == 'TupleV':
            value = objects.TupleV.fromjson(content, typ)
        elif what == 'OptV':
            value = objects.OptV.fromjson(content, typ)
        elif what == 'ListV':
            value = objects.ListV.fromjson(content, typ)
        elif what == 'FuncV':
            value = objects.FuncV.fromjson(content, typ)
        else:
            raise P4UnknownTypeError("Unknown content type")
        return value

    def tojson(self):
        from rpyp4sp import rpyjson, p4specast
        note_map = rpyjson.ROOT_MAP.get_next("typ").get_next("vid")
        typ = self.get_typ()
        assert isinstance(typ, p4specast.Type)
        note_obj = rpyjson.JsonObject2(note_map, typ.tojson(as_bare_typ=True), rpyjson.JsonInt(-1))
        it_array = rpyjson.JsonArray.make(self._tojson_content())
        root_map = rpyjson.ROOT_MAP.get_next("note").get_next("it").get_next("at")
        return rpyjson.JsonObject3(root_map, note_obj, it_array, rpyjson.json_null)

    def _tojson_content(self):
        assert 0, "subclasses must implement _tojson_content"

    def get_typ(self):
        raise NotImplementedError("abstract base class")

    def get_bool(self):
        raise TypeError("not a bool")

    def get_text(self):
        raise TypeError("not a text")

    def get_num(self):
        raise TypeError("not a num")

    def get_list(self):
        raise TypeError("not a list")

    def get_list_len(self):
        raise TypeError("not a list")

    def get_tuple(self):
        raise TypeError("not a tuple")

    def get_struct(self):
        raise TypeError("not a struct")

    def eq(self, other):
        res = self.compare(other)
        assert res in (-1, 0, 1)
        return res == 0

    def compare(self, other):
        #import pdb;pdb.set_trace()
        assert 0

    def _base_compare(self, other):
        if self._compare_tag == other._compare_tag:
            return 0
        if self._compare_tag < other._compare_tag:
            return -1
        return 1

    def tostring(self, short=False, level=0):
        assert 0

    def __str__(self):
        return self.tostring()
