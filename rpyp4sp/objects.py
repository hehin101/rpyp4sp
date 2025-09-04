from rpyp4sp import p4specast
# and vid = int [@@deriving yojson]
# and vnote = { vid : vid; typ : typ' } [@@deriving yojson]


# and value = (value', vnote) note [@@deriving yojson]
# and value' =
#   | BoolV of bool
#   | NumV of Num.t
#   | TextV of string
#   | StructV of valuefield list
#   | CaseV of valuecase
#   | TupleV of value list
#   | OptV of value option
#   | ListV of value list
#   | FuncV of id
# [@@deriving yojson]

# and valuefield = atom * value
# and valuecase = mixop * value list

class W_Base(object):
    # vid: int
    # typ: p4specast.Type
    @staticmethod
    def fromjson(value):
        typ = p4specast.Type.fromjson(value['note']['typ'])
        vid = value['note']['vid'].value_int()
        content = value['it']
        what = content[0].value_string()
        if what == 'BoolV':
            value = W_BoolV.fromjson(content)
        elif what == 'NumV':
            value = W_NumV.fromjson(content)
        elif what == 'TextV':
            value = W_TextV.fromjson(content)
        elif what == 'StructV':
            value = W_StructV.fromjson(content)
        elif what == 'CaseV':
            value = W_CaseV.fromjson(content)
        elif what == 'TupleV':
            value = W_TupleV.fromjson(content)
        elif what == 'OptV':
            value = W_OptV.fromjson(content)
        elif what == 'ListV':
            value = W_ListV.fromjson(content)
        elif what == 'FuncV':
            value = W_FuncV.fromjson(content)
        else:
            raise ValueError("Unknown content type")
        value.vid = vid
        value.typ = typ
        return value

    def get_bool(self):
        raise TypeError("not a bool")

class W_BoolV(W_Base):
    def __init__(self, value, vid=-1, typ=None):
        # TODO: assign a vid if the argument is -1
        self.value = value
        self.vid = vid
        self.typ = typ

    def get_bool(self):
        return self.value
    
    def __repr__(self):
        return "objects.W_BoolV(%r, %r, %r)" % (self.value, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        return W_BoolV(content[1].value_bool())

class W_NumV(W_Base):
    def __init__(self, value, vid=-1, typ=None):
        self.value = value
        self.vid = vid
        self.typ = typ

    def __repr__(self):
        return "objects.W_NumV(%r, %r, %r)" % (self.value, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        return W_NumV(content[1])

class W_TextV(W_Base):
    def __init__(self, value, vid=-1, typ=None):
        self.value = value
        self.vid = vid
        self.typ = typ

    def __repr__(self):
        return "objects.W_TextV(%r, %r, %r)" % (self.value, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        return W_TextV(content[1].value_string())
    
class W_StructV(W_Base):
    def __init__(self, fields, vid=-1, typ=None):
        self.fields = fields
        self.vid = vid
        self.typ = typ

    def __repr__(self):
        return "objects.W_StructV(%r, %r, %r)" % (self.fields, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        fields = []
        import pdb;pdb.set_trace() # TODO: we don't have a test for this yet
        for f in content[1].value_array():
            atom_content, field_content = f.value_array()
            atom = p4specast.Atom.fromjson(atom_content)
            w_field = W_Base.fromjson(field_content)
            fields.append((atom, w_field))
        return W_StructV(fields)

class W_CaseV(W_Base):
    def __init__(self, mixop, values, vid=-1, typ=None):
        self.mixop = mixop
        self.values = values
        self.vid = vid
        self.typ = typ

    def __repr__(self):
        return "objects.W_CaseV(%r, %r, %r, %r)" % (self.mixop, self.values, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        mixop_content, valuelist_content = content[1].value_array()
        mixop = p4specast.MixOp.fromjson(mixop_content)
        values = [W_Base.fromjson(v) for v in valuelist_content.value_array()]
        return W_CaseV(mixop, values)

class W_TupleV(W_Base):
    def __init__(self, elements, vid=-1, typ=None):
        self.elements = elements
        self.vid = vid
        self.typ = typ

    def __repr__(self):
        return "objects.W_TupleV(%r, %r, %r)" % (self.elements, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        import pdb;pdb.set_trace()
        elements = [W_Base.fromjson(e) for e in content[1].value_array()]
        return W_TupleV(elements)

class W_OptV(W_Base):
    def __init__(self, value, vid=-1, typ=None):
        self.w_value = value # type: W_Base | None
        self.vid = vid
        self.typ = typ

    def __repr__(self):
        return "objects.W_OptV(%r, %r, %r)" % (self.w_value, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        w_value = None
        if not content[1].is_null:
            w_value = W_Base.fromjson(content[1])
        return W_OptV(w_value)

class W_ListV(W_Base):
    def __init__(self, elements, vid=-1, typ=None):
        self.elements = elements
        self.vid = vid
        self.typ = typ

    def __repr__(self):
        return "objects.W_ListV(%r, %r, %r)" % (self.elements, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        elements = [W_Base.fromjson(e) for e in content[1].value_array()]
        return W_ListV(elements)

class W_FuncV(W_Base):
    def __init__(self, id, vid=-1, typ=None):
        self.id = id
        self.vid = vid
        self.typ = typ

    def __repr__(self):
        return "objects.W_FuncV(%r, %r, %r)" % (self.id, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        import pdb;pdb.set_trace()
        id = p4specast.Id.fromjson(content[1])
        return W_FuncV(id)
