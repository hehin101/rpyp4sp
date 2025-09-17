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

def indent(level):
    return "  " * level

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

    def get_text(self):
        raise TypeError("not a text")

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

    def tostring(self, short=False, level=0):
        assert 0

    def __str__(self):
        return self.tostring()


class BoolV(BaseV):
    _compare_tag = 0

    def __init__(self, value, vid=-1, typ=None):
        # TODO: assign a vid if the argument is -1
        self.value = value # type: bool
        self.vid = vid # type: int
        self.typ = typ # type: p4specast.Type | None

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

    def tostring(self, short=False, level=0):
        # | BoolV b -> string_of_bool b
        return "true" if self.value else "false"

    @staticmethod
    def fromjson(content):
        return BoolV(content.get_list_item(1).value_bool())

class NumV(BaseV):
    def __init__(self, value, what, vid=-1, typ=None):
        self.value = value # type: integers.Integer
        assert isinstance(what, p4specast.NumTyp)
        self.what = what # type: p4specast.NumTyp
        self.vid = vid # type: int
        self.typ = typ # type: p4specast.Type | None

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

    def tostring(self, short=False, level=0):
        # | NumV n -> Num.string_of_num n
        return self.value.str()

    @staticmethod
    def fromstr(value, what, vid=-1, typ=None):
        return NumV(integers.Integer.fromstr(value), what, vid, typ)

    @staticmethod
    def fromjson(content):
        inner = content.get_list_item(1)
        what = inner.get_list_item(0).value_string()
        if what == 'Int':
            what = p4specast.IntT.INSTANCE
        else:
            assert what == 'Nat'
            what = p4specast.NatT.INSTANCE
        value = inner.get_list_item(1).value_string()
        return NumV.fromstr(value, what)

class TextV(BaseV):
    def __init__(self, value, vid=-1, typ=None):
        self.value = value #type: str
        self.vid = vid # type: int
        self.typ = typ # type: p4specast.Type | None

    def get_text(self):
        return self.value

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

    def tostring(self, short=False, level=0):
        # | TextV s -> "\"" ^ s ^ "\""
        return string_escape_encode(self.value)

    @staticmethod
    def fromjson(content):
        return TextV(content.get_list_item(1).value_string())

class StructV(BaseV):
    def __init__(self, fields, vid=-1, typ=None):
        self.fields = fields # type: list[BaseV]
        self.vid = vid # type: int
        self.typ = typ # type: p4specast.Type | None

    def get_struct(self):
        return self.fields

    def __repr__(self):
        return "objects.StructV(%r, %r, %r)" % (self.fields, self.vid, self.typ)

    def tostring(self, short=False, level=0):
        # | StructV [] -> "{}"
        # | StructV valuefields when short ->
        #     Format.asprintf "{ .../%d }" (List.length valuefields)
        # | StructV valuefields ->
        #     Format.asprintf "{ %s }"
        #       (String.concat ";\n"
        #          (List.mapi
        #             (fun idx (atom, value) ->
        #               let indent = if idx = 0 then "" else indent (level + 1) in
        #               Format.asprintf "%s%s %s" indent (string_of_atom atom)
        #                 (string_of_value ~short ~level:(level + 2) value))
        #             valuefields))
        if not self.fields:
            return "{}"
        if short:
            return "{ .../%d }" % len(self.fields)

        parts = []
        for idx, (atom, value) in enumerate(self.fields):
            if idx == 0:
                indent_str = ""
            else:
                indent_str = indent(level + 1)
            part = "%s%s %s" % (indent_str, atom.value, value.tostring(short, level + 2))
            parts.append(part)

        return "{ %s }" % ";\n".join(parts)

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
        self.mixop = mixop # type: p4specast.MixOp
        self.values = values # type: list[BaseV]
        self.vid = vid # type: int
        self.typ = typ # type: p4specast.Type | None

    def __repr__(self):
        return "objects.CaseV(%r, %r, %r, %r)" % (self.mixop, self.values, self.vid, self.typ)

    def tostring(self, short=False, level=0):
        # | CaseV (mixop, _) when short -> string_of_mixop mixop
        # | CaseV (mixop, values) -> "(" ^ string_of_notval (mixop, values) ^ ")"
        if short:
            return str(self.mixop)

        # Construct notation: mixop with values interspersed
        mixop_phrases = self.mixop.phrases
        result_parts = []
        value_idx = 0

        for phrase in mixop_phrases:
            # Add atoms from this phrase
            phrase_str = "".join([atom.value for atom in phrase])
            if phrase_str:
                result_parts.append(phrase_str)

            # Add corresponding value if available
            if value_idx < len(self.values):
                result_parts.append(self.values[value_idx].tostring(short, level + 1))
                value_idx += 1

        return "(" + " ".join(result_parts) + ")"

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
        self.elements = elements # type: list[BaseV]
        self.vid = vid # type: int
        self.typ = typ # type: p4specast.Type | None

    def compare(self, other):
        if not isinstance(other, TupleV):
            return self._base_compare(other)
        return compares(self.elements, other.elements)

    def __repr__(self):
        return "objects.TupleV(%r, %r, %r)" % (self.elements, self.vid, self.typ)

    def tostring(self, short=False, level=0):
        # | TupleV values ->
        #     Format.asprintf "(%s)"
        #       (String.concat ", "
        #          (List.map (string_of_value ~short ~level:(level + 1)) values))
        element_strs = [element.tostring(short, level + 1) for element in self.elements]
        return "(%s)" % ", ".join(element_strs)

    @staticmethod
    def fromjson(content):
        elements = [BaseV.fromjson(e) for e in content.get_list_item(1).value_array()]
        return TupleV(elements)

class OptV(BaseV):
    def __init__(self, value, vid=-1, typ=None):
        self.value = value # type: BaseV | None
        self.vid = vid # type: int
        self.typ = typ # type: p4specast.Type | None

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

    def tostring(self, short=False, level=0):
        # | OptV (Some value) ->
        #     Format.asprintf "Some(%s)"
        #       (string_of_value ~short ~level:(level + 1) value)
        # | OptV None -> "None"
        if self.value is None:
            return "None"
        else:
            return "Some(%s)" % self.value.tostring(short, level + 1)

    @staticmethod
    def fromjson(content):
        value = None
        if not content.get_list_item(1).is_null:
            value = BaseV.fromjson(content.get_list_item(1))
        return OptV(value)

class ListV(BaseV):
    def __init__(self, elements, vid=-1, typ=None):
        self.elements = elements # type: list[BaseV]
        self.vid = vid # type: int
        self.typ = typ # type: p4specast.Type | None

    def get_list(self):
        return self.elements

    def compare(self, other):
        if not isinstance(other, ListV):
            return self._base_compare(other)
        return compares(self.elements, other.elements)

    def __repr__(self):
        return "objects.ListV(%r, %r, %r)" % (self.elements, self.vid, self.typ)

    def tostring(self, short=False, level=0):
        # | ListV [] -> "[]"
        # | ListV values when short -> Format.asprintf "[ .../%d ]" (List.length values)
        # | ListV values ->
        #     Format.asprintf "[ %s ]"
        #       (String.concat ",\n"
        #          (List.mapi
        #             (fun idx value ->
        #               let indent = if idx = 0 then "" else indent (level + 1) in
        #               indent ^ string_of_value ~short ~level:(level + 2) value)
        #             values))
        if not self.elements:
            return "[]"
        if short:
            return "[ .../%d ]" % len(self.elements)

        parts = []
        for idx, element in enumerate(self.elements):
            if idx == 0:
                indent_str = ""
            else:
                indent_str = indent(level + 1)
            part = indent_str + element.tostring(short, level + 2)
            parts.append(part)

        return "[ %s ]" % ",\n".join(parts)

    @staticmethod
    def fromjson(content):
        elements = [BaseV.fromjson(e) for e in content.get_list_item(1).value_array()]
        return ListV(elements)


class FuncV(BaseV):
    def __init__(self, id, vid=-1, typ=None):
        self.id = id # type: p4specast.Id
        self.vid = vid # type: int
        self.typ = typ # type: p4specast.Type | None

    def __repr__(self):
        return "objects.FuncV(%r, %r, %r)" % (self.id, self.vid, self.typ)

    def tostring(self, short=False, level=0):
        # | FuncV id -> string_of_defid id
        return self.id.value

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


def string_escape_encode(s):
    from rpython.rlib.rstring import StringBuilder
    quote = "'"
    if quote in s and '"' not in s:
        quote = '"'
    buf = StringBuilder(len(s) + 2)

    buf.append(quote)
    startslice = 0

    for i in range(len(s)):
        c = s[i]
        use_bs_char = False # character quoted by backslash

        if c == '\\' or c == quote:
            bs_char = c
            use_bs_char = True
        elif c == '\t':
            bs_char = 't'
            use_bs_char = True
        elif c == '\r':
            bs_char = 'r'
            use_bs_char = True
        elif c == '\n':
            bs_char = 'n'
            use_bs_char = True
        elif not '\x20' <= c < '\x7f':
            n = ord(c)
            if i != startslice:
                buf.append_slice(s, startslice, i)
            startslice = i + 1
            buf.append('\\x')
            buf.append("0123456789abcdef"[n >> 4])
            buf.append("0123456789abcdef"[n & 0xF])

        if use_bs_char:
            if i != startslice:
                buf.append_slice(s, startslice, i)
            startslice = i + 1
            buf.append('\\')
            buf.append(bs_char)

    if len(s) != startslice:
        buf.append_slice(s, startslice, len(s))

    buf.append(quote)

    return buf.build()
