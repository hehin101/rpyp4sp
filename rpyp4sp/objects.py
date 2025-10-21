from rpython.rlib import jit

from rpyp4sp.smalllist import inline_small_list
from rpyp4sp import p4specast, integers
from rpyp4sp.error import P4UnknownTypeError, P4NotImplementedError, P4EvaluationError
from rpyp4sp.base import SubBase, BaseV
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

class BaseVWithTyp(BaseV):
    _attrs_ = ['typ']
    _immutable_fields_ = ['typ']

    # typ: p4specast.Type

    def get_typ(self):
        return self.typ

class BoolV(BaseV):
    _compare_tag = 0

    _attrs_ = ['value']
    _immutable_fields_ = ['value']

    def __init__(self, value):
        self.value = value # type: bool

    @staticmethod
    def make(value, typ):
        if isinstance(typ, p4specast.BoolT):
            if value:
                return BoolV.TRUE
            else:
                return BoolV.FALSE
        else:
            return BoolVWithTyp(value, typ)

    def get_typ(self):
        return p4specast.BoolT.INSTANCE

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
        return "objects.BoolV.make(%r, %r)" % (self.value, self.get_typ())

    def tostring(self, short=False, level=0):
        # | BoolV b -> string_of_bool b
        return "true" if self.value else "false"

    @staticmethod
    def fromjson(content, typ):
        return BoolV.make(content.get_list_item(1).value_bool(), typ)

BoolV.TRUE = BoolV(True)
BoolV.FALSE = BoolV(False)

class BoolVWithTyp(BoolV):
    _attrs_ = ['typ']
    def __init__(self, value, typ):
        BoolV.__init__(self, value)
        self.typ = typ

    def get_typ(self):
        return self.typ

class NumV(BaseV):
    _attrs_ = ['value']

    def __init__(self, value):
        self.value = value # type: integers.Integer

    def get_what(self):
        raise NotImplementedError("abstract method")

    @staticmethod
    def make(value, what, typ):
        if isinstance(typ, p4specast.NumT) and isinstance(what, p4specast.IntT):
            assert type(typ.typ) is type(what)
            return IntV(value, what)
        elif isinstance(typ, p4specast.NumT) and isinstance(what, p4specast.NatT):
            assert type(typ.typ) is type(what)
            return NatV(value, what)
        else:
            return NumVWithTyp(value, what, typ)

    def compare(self, other):
        if not isinstance(other, NumV):
            return self._base_compare(other)
        if self.get_what() != other.get_what():
            raise TypeError("cannot compare different kinds of numbers")
        return self.value.compare(other.value)

    def __repr__(self):
        return "objects.NumV.fromstr(%r, %r, %r)" % (
            self.value.str(), self.get_what(), self.get_typ())

    def get_num(self):
        return self.value

    def tostring(self, short=False, level=0):
        # | NumV n -> Num.string_of_num n
        return self.value.str()

    def eval_unop(self, unop, typ):
        # Evaluate unary numeric operations
        if unop == 'PlusOp':
            return NumV.make(self.value, self.get_what(), typ=typ)
        elif unop == 'MinusOp':
            return NumV.make(self.value.neg(), p4specast.IntT.INSTANCE, typ=typ)
        else:
            assert 0, "Unknown numeric unary operator: %s" % unop

    def eval_binop(self, binop, other, typ):
        # Evaluate binary numeric operations
        from rpyp4sp.error import P4EvaluationError, P4NotImplementedError
        assert isinstance(other, NumV)
        assert type(self.get_what()) is type(other.get_what())
        num_l = self.value
        num_r = other.value
        what = self.get_what()
        if binop == 'AddOp':
            res_num = num_l.add(num_r)
        elif binop == 'SubOp':
            res_num = num_l.sub(num_r)
            what = p4specast.IntT.INSTANCE
        elif binop == 'MulOp':
            res_num = num_l.mul(num_r)
        elif binop == 'DivOp':
            if num_r.int_eq(0):
                raise P4EvaluationError("Modulo with 0")
            remainder = num_l.mod(num_r)
            if not remainder.int_eq(0):
                raise P4EvaluationError("division remainder isn't zero")
            res_num = num_l.div(num_r)
        elif binop == 'ModOp':
            if num_r.int_eq(0):
                raise P4EvaluationError("Modulo with 0")
            res_num = num_l.mod(num_r)
        elif binop == 'PowOp':
            raise P4NotImplementedError("PowOp")
        else:
            assert 0, "should be unreachable"
        return NumV.make(res_num, what, typ=typ)

    def eval_cmpop(self, cmpop, other, typ):
        # Evaluate comparison operations
        assert isinstance(other, NumV)
        assert self.get_what() == other.get_what()
        num_l = self.value
        num_r = other.value
        if cmpop == 'LtOp':
            res = num_l.lt(num_r)
        elif cmpop == 'GtOp':
            res = num_l.gt(num_r)
        elif cmpop == 'LeOp':
            res = num_l.le(num_r)
        elif cmpop == 'GeOp':
            res = num_l.ge(num_r)
        else:
            assert 0, "should be unreachable"
        return BoolV.make(res, typ)

    @staticmethod
    def fromstr(value, what, typ=None):
        return NumV.make(integers.Integer.fromstr(value), what, typ)

    @staticmethod
    def fromjson(content, typ):
        inner = content.get_list_item(1)
        what = inner.get_list_item(0).value_string()
        if what == 'Int':
            what = p4specast.IntT.INSTANCE
        else:
            assert what == 'Nat'
            what = p4specast.NatT.INSTANCE
        value = inner.get_list_item(1).value_string()
        return NumV.fromstr(value, what, typ)

class IntV(NumV):
    def __init__(self, value, what):
        assert isinstance(what, p4specast.IntT)
        NumV.__init__(self, value)

    def get_what(self):
        return p4specast.IntT.INSTANCE

    def get_typ(self):
        return p4specast.IntT.INSTANCE

class NatV(NumV):
    def __init__(self, value, what):
        assert isinstance(what, p4specast.NatT)
        NumV.__init__(self, value)

    def get_what(self):
        return p4specast.NatT.INSTANCE

    def get_typ(self):
        return p4specast.NatT.INSTANCE

class NumVWithTyp(NumV):
    _immutable_fields_ = ['_what', 'typ']
    _attrs_ = ['_what', 'typ']

    def __init__(self, value, what, typ):
        NumV.__init__(self, value)
        assert isinstance(what, p4specast.NumTyp)
        self._what = what
        self.typ = typ

    def get_what(self):
        return self._what

    def get_typ(self):
        return self.typ

class TextV(BaseVWithTyp):
    def __init__(self, value, typ=None):
        self.value = value #type: str
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
        return "objects.TextV(%r, %r)" % (self.value, self.typ)

    def tostring(self, short=False, level=0):
        # | TextV s -> "\"" ^ s ^ "\""
        return string_escape_encode(self.value)

    @staticmethod
    def fromjson(content, typ):
        return TextV(content.get_list_item(1).value_string(), typ)

class StructMap(object):
    def __init__(self, fieldpos):
        self.fieldpos = fieldpos # type: dict[str, int]
        self.next_maps = {} # type: dict[str, StructMap]

    @jit.elidable
    def get_field(self, fieldname):
        return self.fieldpos.get(fieldname, -1)

    @jit.elidable
    def add_field(self, fieldname):
        if fieldname in self.next_maps:
            return self.next_maps[fieldname]
        new_fieldpos = self.fieldpos.copy()
        new_fieldpos[fieldname] = len(new_fieldpos)
        res = StructMap(new_fieldpos)
        self.next_maps[fieldname] = res
        return res

    @jit.elidable_promote('0,1')
    def compare(self, other):
        # lexicographic ordering on field names
        keys_l = list(self.fieldpos.keys())
        keys_r = list(other.fieldpos.keys())
        len_l = len(keys_l)
        len_r = len(keys_r)
        if len_l == len_r == 0:
            return 0
        min_len = min(len_l, len_r)
        for i in range(min_len):
            k_l = keys_l[i]
            k_r = keys_r[i]
            if k_l < k_r:
                return -1
            elif k_l > k_r:
                return 1
        if len_l == len_r:
            return 0
        elif len_l < len_r:
            return -1
        else:
            return 1

    def __repr__(self):
        res = ["objects.StructMap.EMPTY"]
        for k in self.fieldpos.keys():
            res.append(".add_field(%r)" % k)
        return "".join(res)
StructMap.EMPTY = StructMap({})


@inline_small_list(immutable=True)
class StructV(BaseVWithTyp):
    _immutable_fields_ = ['map']

    @jit.unroll_safe
    def __init__(self, map, typ=None):
        assert isinstance(map, StructMap)
        self.map = map # type: StructMap
        self.typ = typ # type: p4specast.Type | None

    def get_struct(self):
        return self

    def get_field(self, atom):
        idx = jit.promote(self.map).get_field(atom.value)
        if idx == -1:
            raise P4EvaluationError("no such field %s" % atom.value)
        return self._get_list(idx)

    def replace_field(self, atom, value):
        idx = jit.promote(self.map).get_field(atom.value)
        if idx == -1:
            raise P4EvaluationError("no such field %s" % atom.value)
        new_fields = self._get_full_list()[:]
        new_fields[idx] = value
        return StructV.make(new_fields, self.map, self.typ)


    def __repr__(self):
        size = self._get_size_list()
        if size == 0:
            return "objects.StructV.make0(%r, %r)" % (self.map, self.typ)
        elif size == 1:
            return "objects.StructV.make1(%r, %r, %r)" % (self._get_list(0), self.map, self.typ)
        elif size == 2:
            return "objects.StructV.make2(%r, %r, %r, %r)" % (self._get_list(0), self._get_list(1), self.map, self.typ)
        else:
            return "objects.StructV.make(%r, %r, %r)" % (self._get_full_list(), self.map, self.typ)

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
        if not self._get_size_list():
            return "{}"
        if short:
            return "{ .../%d }" % self._get_size_list()

        parts = []
        for fieldname, index in self.map.fieldpos.items():
            value = self._get_list(index)
            if index == 0:
                indent_str = ""
            else:
                indent_str = indent(level + 1)
            part = "%s%s %s" % (indent_str, fieldname, value.tostring(short, level + 2))
            parts.append(part)

        return "{ %s }" % ";\n".join(parts)

    @staticmethod
    def fromjson(content, typ):
        values = []
        map = StructMap.EMPTY
        for f in content.get_list_item(1).value_array():
            atom_content, field_content = f.value_array()
            atom = p4specast.AtomT.fromjson(atom_content)
            field = BaseV.fromjson(field_content)
            values.append(field)
            map = map.add_field(atom.value)
        return StructV.make(values, map, typ)

    def compare(self, other):
        if not isinstance(other, StructV):
            return self._base_compare(other)
        res = self.map.compare(other.map)
        if res:
            return res
        return compares(self._get_full_list(), other._get_full_list())

class MixopTyp(object):
    _attrs_ = ['mixop', 'typ']
    def __init__(self, mixop, typ=None):
        self.mixop = mixop # type: p4specast.MixOp
        self.typ = typ # type: p4specast.Type | None

MixopTyp.CACHE = {}

@inline_small_list(immutable=True)
class CaseV(BaseV):
    _attrs_ = ['mixoptyp']
    _immutable_ = True
    _immutable_fields_ = ['mixoptyp']
    def __init__(self, mixop, typ=None):
        mixop_typ = (mixop.tostring(), typ.tostring())
        if mixop_typ not in MixopTyp.CACHE:
            MixopTyp.CACHE[mixop_typ] = MixopTyp(mixop, typ)
        self.mixoptyp = MixopTyp.CACHE[mixop_typ] # type: MixopTyp

    def __repr__(self):
        size = self._get_size_list()
        if size == 0:
            return "objects.CaseV.make0(%r, %r)" % (self.mixoptyp.mixop, self.mixoptyp.typ)
        elif size == 1:
            return "objects.CaseV.make1(%r, %r, %r)" % (self._get_list(0), self.mixoptyp.mixop, self.mixoptyp.typ)
        elif size == 2:
            return "objects.CaseV.make2(%r, %r, %r, %r)" % (self._get_list(0), self._get_list(1), self.mixoptyp.mixop, self.mixoptyp.typ)
        else:
            return "objects.CaseV.make(%r, %r, %r)" % (self._get_full_list(), self.mixoptyp.mixop, self.mixoptyp.typ)

    def tostring(self, short=False, level=0):
        # | CaseV (mixop, _) when short -> string_of_mixop mixop
        # | CaseV (mixop, values) -> "(" ^ string_of_notval (mixop, values) ^ ")"
        if short:
            return self.mixoptyp.mixop.tostring()

        # Construct notation: mixop with values interspersed
        mixop_phrases = self.mixoptyp.mixop.phrases
        result_parts = []
        value_idx = 0

        for phrase in mixop_phrases:
            # Add atoms from this phrase
            phrase_str = "".join([atom.value for atom in phrase])
            if phrase_str:
                result_parts.append(phrase_str)

            # Add corresponding value if available
            if value_idx < self._get_size_list():
                result_parts.append(self._get_list(value_idx).tostring(short, level + 1))
                value_idx += 1

        return "(" + " ".join(result_parts) + ")"

    @staticmethod
    def fromjson(content, typ):
        mixop_content, valuelist_content = content.get_list_item(1).value_array()
        mixop = p4specast.MixOp.fromjson(mixop_content)
        values = [BaseV.fromjson(v) for v in valuelist_content.value_array()]
        return CaseV.make(values, mixop, typ)

    def compare(self, other):
        if not isinstance(other, CaseV):
            return self._base_compare(other)
        # let cmp_mixop = Mixop.compare mixop_l mixop_r in
        cmp_mixop = self.mixoptyp.mixop.compare(other.mixoptyp.mixop)
        # if cmp_mixop <> 0 then cmp_mixop else compares values_l values_r
        if cmp_mixop != 0:
            return cmp_mixop
        elif self._get_size_list() == 0:
            assert other._get_size_list() == 0
            return 0
        elif self._get_size_list() == 1:
            assert other._get_size_list() == 1
            return self._get_list(0).compare(other._get_list(0))
        else:
            return compares(self._get_full_list(), other._get_full_list())

    def get_typ(self):
        return self.mixoptyp.typ


@inline_small_list(immutable=True)
class TupleV(BaseVWithTyp):
    _immutable_fields_ = []
    def __init__(self, typ=None):
        self.typ = typ # type: p4specast.Type | None

    def get_tuple(self):
        return self._get_full_list()

    def compare(self, other):
        if not isinstance(other, TupleV):
            return self._base_compare(other)
        return compares(self._get_full_list(), other._get_full_list())

    def __repr__(self):
        size = self._get_size_list()
        if size == 0:
            return "objects.TupleV.make0(%r)" % (self.typ)
        elif size == 1:
            return "objects.TupleV.make1(%r, %r)" % (self._get_list(0), self.typ)
        elif size == 2:
            return "objects.TupleV.make2(%r, %r, %r)" % (self._get_list(0), self._get_list(1), self.typ)
        else:
            return "objects.TupleV.make(%r, %r)" % (self._get_full_list(), self.typ)

    def tostring(self, short=False, level=0):
        # | TupleV values ->
        #     Format.asprintf "(%s)"
        #       (String.concat ", "
        #          (List.map (string_of_value ~short ~level:(level + 1)) values))
        element_strs = [self._get_list(i).tostring(short, level + 1) for i in range(self._get_size_list())]
        return "(%s)" % ", ".join(element_strs)

    @staticmethod
    def fromjson(content, typ):
        elements = [BaseV.fromjson(e) for e in content.get_list_item(1).value_array()]
        return TupleV.make(elements, typ)

class OptV(BaseVWithTyp):
    def __init__(self, value, typ=None):
        self.value = value # type: BaseV | None
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
        return "objects.OptV(%r, %r)" % (self.value, self.typ)

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
    def fromjson(content, typ):
        value = None
        if not content.get_list_item(1).is_null:
            value = BaseV.fromjson(content.get_list_item(1))
        return OptV(value, typ)

# just optimize lists of size 0, 1, arbitrary
@inline_small_list(immutable=True, sizemax=2, factoryname='_make')
class ListV(BaseVWithTyp):
    _immutable_fields_ = []
    def __init__(self, typ=None):
        self.typ = typ # type: p4specast.Type | None

    @staticmethod
    def make0(typ):
        return typ.empty_list_value()

    @staticmethod
    def make1(val, typ):
        return ListV._make1(val, typ)

    @staticmethod
    def make2(val0, val1, typ):
        return ListV._make2(val0, val1, typ)

    @staticmethod
    def make(values, typ):
        if not values and isinstance(typ, p4specast.IterT):
            return typ.empty_list_value()
        return ListV._make(values, typ)

    def get_list(self):
        return self._get_full_list()

    def get_list_len(self):
        return self._get_size_list()

    def compare(self, other):
        if not isinstance(other, ListV):
            return self._base_compare(other)
        return compares(self._get_full_list(), other._get_full_list())

    def __repr__(self):
        size = self._get_size_list()
        if size == 0:
            return "objects.ListV.make0(%r)" % (self.typ)
        elif size == 1:
            return "objects.ListV.make1(%r, %r)" % (self._get_list(0), self.typ)
        else:
            return "objects.ListV.make(%r, %r)" % (self._get_full_list(), self.typ)

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
        if not self._get_size_list():
            return "[]"
        if short:
            return "[ .../%d ]" % self._get_size_list()

        parts = []
        for idx in range(self._get_size_list()):
            element = self._get_list(idx)
            if idx == 0:
                indent_str = ""
            else:
                indent_str = indent(level + 1)
            part = indent_str + element.tostring(short, level + 2)
            parts.append(part)

        return "[ %s ]" % ",\n".join(parts)

    @staticmethod
    def fromjson(content, typ):
        elements = [BaseV.fromjson(e) for e in content.get_list_item(1).value_array()]
        return ListV.make(elements, typ)


class FuncV(BaseVWithTyp):
    def __init__(self, id, typ=None):
        self.id = id # type: p4specast.Id
        self.typ = typ # type: p4specast.Type | None

    def __repr__(self):
        return "objects.FuncV(%r, %r)" % (self.id, self.typ)

    def tostring(self, short=False, level=0):
        # | FuncV id -> string_of_defid id
        return self.id.value

    @staticmethod
    def fromjson(content, typ):
        id = p4specast.Id.fromjson(content.get_list_item(1))
        return FuncV(id, typ)

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
    if len_l <= 1 and len_r <= 1:
        if len_l == len_r == 0:
            return 0
        if len_l == len_r == 1:
            return values_l[0].compare(values_r[0])
        # if we reach here, one list is size 1, the other size 0
        if len_l < len_r:
            return -1
        return 1
    return _compares(values_l, values_r, len_l, len_r)

def _compares(values_l, values_r, len_l, len_r):
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
