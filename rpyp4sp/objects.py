from rpyp4sp import p4specast, integers
from rpyp4sp.error import P4UnknownTypeError
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

class BaseV(object):
    _attrs_ = ['typ', 'vid']
    # vid: int
    # typ: p4specast.Type
    @staticmethod
    def fromjson(value):
        typ = p4specast.Type.fromjson(value.get_dict_value('note').get_dict_value('typ'))
        vid = value.get_dict_value('note').get_dict_value('vid').value_int()
        content = value.get_dict_value('it')
        what = content.get_list_item(0).value_string()
        if what == 'BoolV':
            value = BoolV.fromjson(content)
        elif what == 'NumV':
            value = NumV.fromjson(content)
        elif what == 'TextV':
            value = TextV.fromjson(content)
        elif what == 'StructV':
            value = StructV.fromjson(content)
        elif what == 'CaseV':
            value = CaseV.fromjson(content)
        elif what == 'TupleV':
            value = TupleV.fromjson(content)
        elif what == 'OptV':
            value = OptV.fromjson(content)
        elif what == 'ListV':
            value = ListV.fromjson(content)
        elif what == 'FuncV':
            value = FuncV.fromjson(content)
        else:
            raise P4UnknownTypeError("Unknown content type")
        value.vid = vid
        value.typ = typ
        return value

    def get_bool(self):
        raise TypeError("not a bool")

    def get_num(self):
        raise TypeError("not a num")

    def get_list(self):
        raise TypeError("not a list")

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


class BoolV(BaseV):
    _compare_tag = 0

    def __init__(self, value, vid=-1, typ=None):
        # TODO: assign a vid if the argument is -1
        self.value = value
        self.vid = vid
        self.typ = typ

    def compare(self, other):
        if not isinstance(other, BoolV):
            return self._base_compare(other)
        if self.value == other.value:
            return 0
        elif self.value < other.value:
            return -1
        else:
            return 1

    def get_bool(self):
        return self.value

    def __repr__(self):
        return "objects.BoolV(%r, %r, %r)" % (self.value, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        return BoolV(content.get_list_item(1).value_bool())

class NumV(BaseV):
    def __init__(self, value, what, vid=-1, typ=None):
        self.value = value # type: integer.Integer
        assert what in ('Int', 'Nat')
        self.what = what # type: str
        self.vid = vid # type: int
        self.typ = typ # type: Type | None

    def compare(self, other):
        if not isinstance(other, NumV):
            return self._base_compare(other)
        if self.what != other.what:
            raise TypeError("cannot compare different kinds of numbers")
        return self.value.compare(other.value)

    def __repr__(self):
        return "objects.NumV.fromstr(%r, %r, %r, %r)" % (
            self.value.str(), self.what, self.vid, self.typ)

    def get_num(self):
        return self.value

    @staticmethod
    def fromstr(value, what, vid=-1, typ=None):
        return NumV(integers.Integer.fromstr(value), what, vid, typ)

    @staticmethod
    def fromjson(content):
        inner = content.get_list_item(1)
        what = inner.get_list_item(0).value_string() # 'Int' or 'Nat'
        value = inner.get_list_item(1).value_string()
        return NumV.fromstr(value, what)

class TextV(BaseV):
    def __init__(self, value, vid=-1, typ=None):
        self.value = value
        self.vid = vid
        self.typ = typ

    def compare(self, other):
        if not isinstance(other, TextV):
            return self._base_compare(other)
        if self.value == other.value:
            return 0
        elif self.value < other.value:
            return -1
        else:
            return 1

    def __repr__(self):
        return "objects.TextV(%r, %r, %r)" % (self.value, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        return TextV(content.get_list_item(1).value_string())

class StructV(BaseV):
    def __init__(self, fields, vid=-1, typ=None):
        self.fields = fields
        self.vid = vid
        self.typ = typ

    def get_struct(self):
        return self.fields

    def __repr__(self):
        return "objects.StructV(%r, %r, %r)" % (self.fields, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        fields = []
        for f in content.get_list_item(1).value_array():
            atom_content, field_content = f.value_array()
            atom = p4specast.AtomT.fromjson(atom_content)
            field = BaseV.fromjson(field_content)
            fields.append((atom, field))
        return StructV(fields)

    def compare(self, other):
        if not isinstance(other, StructV):
            return self._base_compare(other)
        def split_fields(fields):
            atoms, values = [], []
            for atom, value in fields:
                atoms.append(atom)
                values.append(value)
            return atoms, values
        atoms_l, values_l = split_fields(self.fields)
        atoms_r, values_r = split_fields(other.fields)
        res = atom_compares(atoms_l, atoms_r)
        if res:
            return res
        return compares(values_l, values_r)

class CaseV(BaseV):
    def __init__(self, mixop, values, vid=-1, typ=None):
        self.mixop = mixop
        self.values = values
        self.vid = vid
        self.typ = typ

    def __repr__(self):
        return "objects.CaseV(%r, %r, %r, %r)" % (self.mixop, self.values, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        mixop_content, valuelist_content = content.get_list_item(1).value_array()
        mixop = p4specast.MixOp.fromjson(mixop_content)
        values = [BaseV.fromjson(v) for v in valuelist_content.value_array()]
        return CaseV(mixop, values)

    def compare(self, other):
        if not isinstance(other, CaseV):
            return self._base_compare(other)
        # let cmp_mixop = Mixop.compare mixop_l mixop_r in
        cmp_mixop = self.mixop.compare(other.mixop)
        # if cmp_mixop <> 0 then cmp_mixop else compares values_l values_r
        if cmp_mixop != 0:
            return cmp_mixop
        else:
            return compares(self.values, other.values)


class TupleV(BaseV):
    def __init__(self, elements, vid=-1, typ=None):
        self.elements = elements
        self.vid = vid
        self.typ = typ

    def compare(self, other):
        if not isinstance(other, TupleV):
            return self._base_compare(other)
        return compares(self.elements, other.elements)

    def __repr__(self):
        return "objects.TupleV(%r, %r, %r)" % (self.elements, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        elements = [BaseV.fromjson(e) for e in content.get_list_item(1).value_array()]
        return TupleV(elements)

class OptV(BaseV):
    def __init__(self, value, vid=-1, typ=None):
        self.value = value # type: BaseV | None
        self.vid = vid
        self.typ = typ

    def compare(self, other):
        if not isinstance(other, OptV):
            return self._base_compare(other)
        if self.value is not None and other.value is not None:
            return self.value.compare(other.value)
        elif self.value is not None and other.value is None:
            return 1
        elif self.value is None and other.value is not None:
            return -1
        else:  # both None
            return 0


    def __repr__(self):
        return "objects.OptV(%r, %r, %r)" % (self.value, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        value = None
        if not content.get_list_item(1).is_null:
            value = BaseV.fromjson(content.get_list_item(1))
        return OptV(value)

class ListV(BaseV):
    def __init__(self, elements, vid=-1, typ=None):
        self.elements = elements
        self.vid = vid
        self.typ = typ

    def get_list(self):
        return self.elements

    def compare(self, other):
        if not isinstance(other, ListV):
            return self._base_compare(other)
        return compares(self.elements, other.elements)

    def __repr__(self):
        return "objects.ListV(%r, %r, %r)" % (self.elements, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        elements = [BaseV.fromjson(e) for e in content.get_list_item(1).value_array()]
        return ListV(elements)


class FuncV(BaseV):
    def __init__(self, id, vid=-1, typ=None):
        self.id = id
        self.vid = vid
        self.typ = typ

    def __repr__(self):
        return "objects.FuncV(%r, %r, %r)" % (self.id, self.vid, self.typ)

    @staticmethod
    def fromjson(content):
        id = p4specast.Id.fromjson(content.get_list_item(1))
        return FuncV(id)

def atom_compares(atoms_l, atoms_r):
    len_l = len(atoms_l)
    len_r = len(atoms_r)
    min_len = min(len_l, len_r)
    for i in range(min_len):
        cmp = atoms_l[i].compare(atoms_r[i])
        if cmp != 0:
            return cmp
    if len_l == len_r:
        return 0
    elif len_l < len_r:
        return -1
    else:
        return 1

def compares(values_l, values_r):
    # type: (list[BaseV], list[BaseV]) -> int
    # lexicographic ordering, iterative version
    len_l = len(values_l)
    len_r = len(values_r)
    min_len = min(len_l, len_r)
    for i in range(min_len):
        cmp = values_l[i].compare(values_r[i])
        if cmp != 0:
            return cmp
    if len_l == len_r:
        return 0
    elif len_l < len_r:
        return -1
    else:
        return 1
    # match (values_l, values_r) with
    #   | [], [] -> 0
    #   | [], _ :: _ -> -1
    #   | _ :: _, [] -> 1
    #   | value_l :: values_l, value_r :: values_r ->
    #       let cmp = compare value_l value_r in
    #       if cmp <> 0 then cmp else compares values_l values_r
