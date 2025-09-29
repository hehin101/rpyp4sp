from __future__ import print_function
from rpython.rlib import jit
from rpython.tool.pairtype import extendabletype
from rpyp4sp import integers
from rpyp4sp.error import P4UnknownTypeError, P4NotImplementedError

def ast_anywhere_in_list(l):
    for index, el in enumerate(l):
        if isinstance(el, (list, tuple)):
            if ast_anywhere_in_list(el):
                return True
        elif isinstance(el, AstBase):
            return True
    return False

def flatten_list_with_access_string(l, prefix):
    for index, el in enumerate(l):
        path = "%s[%s]" % (prefix, index)
        if isinstance(el, (list, tuple)):
            for sub in flatten_list_with_access_string(el, path):
                yield sub
        else:
            yield el, path

class AstBase(object):
    __metaclass__ = extendabletype
    _attrs_ = []

    def __eq__(self, other):
        return type(self) == type(other) and self.__dict__ == other.__dict__

    def __ne__(self, other):
        return not (self == other)

    def view(self):
        from rpython.translator.tool.make_dot import DotGen
        from dotviewer import graphclient
        import pytest
        dotgen = DotGen('G')
        self._dot(dotgen)
        p = pytest.ensuretemp("pyparser").join("temp.dot")
        p.write(dotgen.generate(target=None))
        graphclient.display_dot_file(str(p))

    def _dot(self, dotgen):
        arcs = []
        label = [self.__class__.__name__]
        for key, value in self.__dict__.items():
            #if key == 'phantom':
            #    continue
            if isinstance(value, (Region, Position)):
                continue
            if isinstance(value, AstBase):
                arcs.append((value, key))
                value._dot(dotgen)
            elif isinstance(value, list) and ast_anywhere_in_list(value):
                for item, path in flatten_list_with_access_string(value, key):
                    arcs.append((item, path))
                    item._dot(dotgen)
            else:
                label.append("%s = %r" % (key, value))
        dotgen.emit_node(str(id(self)), shape="box", label = "\n".join(label))
        for target, label in arcs:
            dotgen.emit_edge(str(id(self)), str(id(target)), label)

    def eq(self, other):
        return self.compare(other) == 0

    def compare(self, other):
        raise P4NotImplementedError('abstract base')


def define_enum(basename, *names):
    class Base(AstBase):
        @staticmethod
        def fromjson(value):
            content, = value.value_array()
            content = content.value_string()
            for name, cls in unrolling_tups:
                if name == content:
                    return cls.INSTANCE
            assert 0

        def tojson(self):
            from rpyp4sp import rpyjson
            return rpyjson.JsonArray([rpyjson.JsonString(self.__class__.__name__)])

        def __repr__(self):
            return "p4specast." + self.__class__.__name__ + ".INSTANCE"
    Base.__name__ = basename
    subs = []
    for name in names:
        class Sub(Base):
            pass
        Sub.__name__ = name
        Sub.INSTANCE = Sub()
        subs.append(Sub)
    unrolling_tups = [(names[i], cls) for i, cls in enumerate(subs)]
    return [Base] + subs


# type pos = { file : string; line : int; column : int } [@@deriving yojson]


class Position(AstBase):
    def __init__(self, file, line, column):
        self.file = file # type: str
        self.line = line # type: int
        self.column = column # type: int

    @staticmethod
    def fromjson(value):
        return Position(value.get_dict_value('file').value_string(), value.get_dict_value('line').value_int(), value.get_dict_value('column').value_int())

    def tojson(self):
        from rpyp4sp import rpyjson
        file_map = rpyjson.ROOT_MAP.get_next("file").get_next("line").get_next("column")
        return rpyjson.JsonObject3(file_map, rpyjson.JsonString(self.file), rpyjson.JsonInt(self.line), rpyjson.JsonInt(self.column))

    def has_information(self):
        return self.file != '' or self.line != 0 or self.column != 0

    def __repr__(self):
        return "p4specast.Position(%r, %d, %d)" % (self.file, self.line, self.column)

# type region = { left : pos; right : pos } [@@deriving yojson]

class Region(AstBase):
    def __init__(self, left, right):
        self.left = left # type: Position
        self.right = right # type: Position

    @staticmethod
    def fromjson(value):
        # {
        #  "left": { "file": "spec/0-aux.watsup", "line": 18, "column": 5 },
        #  "right": { "file": "spec/0-aux.watsup", "line": 18, "column": 9 }
        # }
        left = Position.fromjson(value.get_dict_value('left'))
        right = Position.fromjson(value.get_dict_value('right'))
        if not left.has_information() and not right.has_information():
            return NO_REGION
        return Region(left, right)

    def tojson(self):
        from rpyp4sp import rpyjson
        region_map = rpyjson.ROOT_MAP.get_next("left").get_next("right")
        return rpyjson.JsonObject2(region_map, self.left.tojson(), self.right.tojson())

    @staticmethod
    def line_span(file, line, column_start, column_end):
        return Region(Position(file, line, column_start), Position(file, line, column_end))

    def is_line_span(self):
        return (self.left.has_information() and
                self.right.has_information() and
                self.left.file == self.right.file and
                self.left.line == self.right.line)

    def has_information(self):
        return self.left.has_information() or self.right.has_information()

    def __repr__(self):
        if self.left.has_information() or self.right.has_information():
            if self.left.file == self.right.file and self.left.line == self.right.line:
                return "p4specast.Region.line_span(%r, %d, %d, %d)" % (
                    self.left.file, self.left.line, self.left.column, self.right.column)
            return "p4specast.Region(%s, %s)" % (self.left, self.right)
        else:
            return "p4specast.NO_REGION"

NO_REGION = Region(Position('', 0, 0), Position('', 0, 0))


# type ('a, 'b, 'c) info = { it : 'a; note : 'b; at : 'c } [@@deriving yojson]
# type 'a phrase = ('a, unit, region) info [@@deriving yojson]

# type id = id' phrase [@@deriving yojson]
# and id' = string [@@deriving yojson]

class Id(AstBase):
    _attrs_ = ['value', 'region']
    def __init__(self, value, region):
        self.value = value # type: str
        self.region = region # type: Region

    @staticmethod
    def fromjson(value):
        """ example:{
        "it": "sum",
        "note": null,
        "at": {
          "left": { "file": "spec/0-aux.watsup", "line": 18, "column": 5 },
          "right": { "file": "spec/0-aux.watsup", "line": 18, "column": 9 }
        }
      },"""
        region = Region.fromjson(value.get_dict_value('at'))
        return Id(
            value.get_dict_value('it').value_string(),
            region
        )

    def tojson(self):
        from rpyp4sp import rpyjson
        id_map = rpyjson.ROOT_MAP.get_next("it").get_next("note").get_next("at")
        return rpyjson.JsonObject3(id_map, rpyjson.JsonString(self.value), rpyjson.json_null, self.region.tojson())

    def __repr__(self):
        return "p4specast.Id(%r, %s)" % (self.value, self.region)

class TParam(AstBase):
    def __init__(self, value, region):
        self.value = value # type: str
        self.region = region # type: Region

    def tostring(self):
        # and string_of_tparam tparam = tparam.it
        return self.value

    @staticmethod
    def fromjson(value):
        return TParam(
            value.get_dict_value('it').value_string(),
            Region.fromjson(value.get_dict_value('at'))
        )

    def __repr__(self):
        return "p4specast.TParam(value=%s, region=%s)" % (self.value, self.region)

# a targ is the same as a typ!
# and targ = targ' phrase [@@deriving yojson]
# and targ' = typ' [@@deriving yojson]


# type iter =
#   | Opt       (* `?` *)
#   | List      (* `*` *)

Iter, Opt, List = define_enum('Iter', 'Opt', 'List')

def string_of_iter(iter):
    # let string_of_iter iter = match iter with Opt -> "?" | List -> "*"
    if isinstance(iter, Opt):
        return "?"
    elif isinstance(iter, List):
        return "*"
    else:
        assert 0, "Unknown iter type: %s" % iter

def string_of_tparams(tparams):
    # and string_of_tparams tparams =
    #   match tparams with
    #   | [] -> ""
    #   | tparams ->
    #       "<" ^ String.concat ", " (List.map string_of_tparam tparams) ^ ">"
    if not tparams:
        return ""
    return "<%s>" % ", ".join([tp.tostring() for tp in tparams])

def string_of_cases(cases, level=0):
    # and string_of_cases ?(level = 0) cases =
    #   cases
    #   |> List.mapi (fun idx case -> string_of_case ~level ~index:(idx + 1) case)
    #   |> String.concat "\n\n"
    return "\n\n".join([case.tostring(level=level, index=idx+1) for idx, case in enumerate(cases)])

def string_of_instrs(instrs, level=0):
    # and string_of_instrs ?(level = 0) instrs =
    #   instrs
    #   |> List.mapi (fun idx instr -> string_of_instr ~level ~index:(idx + 1) instr)
    #   |> String.concat "\n\n"
    return "\n\n".join([instr.tostring(level=level, index=idx+1) for idx, instr in enumerate(instrs)])

def string_of_iterexps(iterexps):
    # and string_of_iterexps iterexps =
    #   iterexps |> List.map string_of_iterexp |> String.concat ""
    if not iterexps:
        return ""
    return "".join([iterexp.tostring() for iterexp in iterexps])

# type var = id * typ * iter list

class Var(AstBase):
    def __init__(self, id, typ, iter):
        self.id = id
        self.typ = typ
        self.iter = iter

    def tostring(self):
        # let string_of_var (id, _typ, iters) =
        #   string_of_varid id ^ String.concat "" (List.map string_of_iter iters)
        iters_str = "".join([string_of_iter(i) for i in self.iter])
        return "%s%s" % (self.id.value, iters_str)

    def __repr__(self):
        return "p4specast.Var(id=%s, typ=%s, iter=%s)" % (self.id, self.typ, self.iter)

    @staticmethod
    def fromjson(content):
        return Var(
            id=Id.fromjson(content.get_list_item(0)),
            typ=Type.fromjson(content.get_list_item(1)),
            iter=[Iter.fromjson(i) for i in content.get_list_item(2).value_array()]
        )

# type def = def' phrase
# and def' =
#   (* `syntax` id `<` list(tparam, `,`) `>` `=` deftyp *)
#   | TypD of id * tparam list * deftyp
#   (* `relation` id `:` mixop `hint(input` `%`int* `)` list(exp, `,`) `:` instr* *)
#   | RelD of id * (mixop * int list) * exp list * instr list
#   (* `dec` id `<` list(tparam, `,`) `>` list(param, `,`) `:` typ instr* *)
#  | DecD of id * tparam list * arg list * instr list

class Def(AstBase):
    @staticmethod
    def fromjson(value):
        assert value.get_dict_value('note').is_null
        region = Region.fromjson(value.get_dict_value('at'))
        content = value.get_dict_value('it')
        what = content.get_list_item(0).value_string()
        if what == 'DecD':
            ast = DecD.fromjson(content)
        elif what == 'TypD':
            ast = TypD.fromjson(content)
        elif what == 'RelD':
            ast = RelD.fromjson(content)
        else:
            raise P4UnknownTypeError("Unknown Def type: %s" % what)
        ast.region = region
        return ast


class TypD(Def):
    def __init__(self, id, tparams, deftyp):
        self.id = id            # type: Id
        self.tparams = tparams  # type: list[tparam]
        self.deftyp = deftyp    # type: deftyp

    def __repr__(self):
        return "p4specast.TypD(%s, %s, %s)" % (self.id, self.tparams, self.deftyp)

    @staticmethod
    def fromjson(value):
        _, id, tparams_value, deftype_value = value.unpack(4)
        tparams = [TParam.fromjson(p) for p in tparams_value]
        deftyp = DefTyp.fromjson(deftype_value)
        return TypD(
            id=Id.fromjson(id),
            tparams=tparams,
            deftyp=deftyp
        )


class RelD(Def):
    def __init__(self, id, mixop, inputs, exps, instrs):
        self.id = id            # type: Id
        self.mixop = mixop      # type: MixOp
        self.inputs = inputs    # type: list[Input]
        self.exps = exps        # type: list[Exp]
        self.instrs = instrs    # type: list[Instr]

    def __repr__(self):
        return "p4specast.RelD(%r, %r, %r, %r, %r)" % (self.id, self.mixop, self.inputs, self.exps, self.instrs)

    @staticmethod
    def fromjson(value):
        _, id, mixop_and_ints, exps_value, instrs_value = value.unpack(5)
        mixop = MixOp.fromjson(mixop_and_ints.get_list_item(0))
        inputs = [i.value_int() for i in mixop_and_ints.get_list_item(1).value_array()]
        exps = [Exp.fromjson(e) for e in exps_value]
        instrs = [Instr.fromjson(i) for i in instrs_value]
        return RelD(
            id=Id.fromjson(id),
            mixop=mixop,
            inputs=inputs,
            exps=exps,
            instrs=instrs
        )

class DecD(Def):
    def __init__(self, id, tparams, args, instrs):
        self.id = id            # type: Id
        self.tparams = tparams  # type: list[tparam]
        self.args = args        # type: list[arg]
        self.instrs = instrs    # type: list[instr]

    def __repr__(self):
        return "p4specast.DecD(%r, %r, %r, %r)" % (self.id, self.tparams, self.args, self.instrs)

    @staticmethod
    def fromjson(value):
        _, id, tparams_value, args_value, instrs_value = value.unpack(5)
        tparams = [TParam.fromjson(p) for p in tparams_value]
        args = [Arg.fromjson(a) for a in args_value]
        instrs = [Instr.fromjson(i) for i in instrs_value]
        return DecD(
            id=Id.fromjson(id),
            tparams=tparams,
            args=args,
            instrs=instrs
        )

# and arg = arg' phrase
# and arg' =
#   | ExpA of exp   (* exp *)
#   | DefA of id    (* `$`id *)

class Arg(AstBase):
    def tostring(self):
        assert 0  # abstract method

    @staticmethod
    def fromjson(value):
        assert value.get_dict_value('note').is_null
        region = Region.fromjson(value.get_dict_value('at'))
        content = value.get_dict_value('it')
        what = content.get_list_item(0).value_string()
        if what == 'ExpA':
            return ExpA.fromjson(content)
        elif what == 'DefA':
            return DefA.fromjson(content)
        else:
            raise P4UnknownTypeError("Unknown Arg type: %s" % what)

class ExpA(Arg):
    def __init__(self, exp):
        self.exp = exp # typ: Exp

    def tostring(self):
        # | ExpP typ -> string_of_typ typ (but this is ExpA with exp, so return exp)
        return self.exp.tostring()

    def __repr__(self):
        return "p4specast.ExpA(%r)" % (self.exp,)

    @staticmethod
    def fromjson(value):
        _, exp_value = value.unpack(2)
        return ExpA(
            exp=Exp.fromjson(exp_value)
        )

class DefA(Arg):
    def __init__(self, id):
        self.id = id # typ: Id

    def tostring(self):
        # | DefP (defid, tparams, params, typ) -> ... (but this is DefA with just id)
        return "$%s" % self.id.value

    def __repr__(self):
        return "p4specast.DefA(%r)" % (self.id,)

    @staticmethod
    def fromjson(value):
        _, id_value = value.unpack(2)
        return DefA(
            id=Id.fromjson(id_value)
        )

# and exp = (exp', typ') note_phrase
# and exp' =
#   | BoolE of bool                         (* bool *)
#   | NumE of num                           (* num *)
#   | TextE of text                         (* text *)
#   | VarE of id                            (* varid *)
#   | UnE of unop * optyp * exp             (* unop exp *)
#   | BinE of binop * optyp * exp * exp     (* exp binop exp *)
#   | CmpE of cmpop * optyp * exp * exp     (* exp cmpop exp *)
#   | UpCastE of typ * exp                  (* exp as typ *)
#   | DownCastE of typ * exp                (* exp as typ *)
#   | SubE of exp * typ                     (* exp `<:` typ *)
#   | MatchE of exp * pattern               (* exp `matches` pattern *)
#   | TupleE of exp list                    (* `(` exp* `)` *)
#   | CaseE of notexp                       (* notexp *)
#   | StrE of (atom * exp) list             (* { expfield* } *)
#   | OptE of exp option                    (* exp? *)
#   | ListE of exp list                     (* `[` exp* `]` *)
#   | ConsE of exp * exp                    (* exp `::` exp *)
#   | CatE of exp * exp                     (* exp `++` exp *)
#   | MemE of exp * exp                     (* exp `<-` exp *)
#   | LenE of exp                           (* `|` exp `|` *)
#   | DotE of exp * atom                    (* exp.atom *)
#   | IdxE of exp * exp                     (* exp `[` exp `]` *)
#   | SliceE of exp * exp * exp             (* exp `[` exp `:` exp `]` *)
#   | UpdE of exp * path * exp              (* exp `[` path `=` exp `]` *)
#   | CallE of id * targ list * arg list    (* $id`<` targ* `>``(` arg* `)` *)
#   | IterE of exp * iterexp                (* exp iterexp *)


class Exp(AstBase):
    _attrs_ = ['typ', 'region']
    # has .typ (with is in 'note' field of json) and a region

    @staticmethod
    def fromjson(value):
        typ = Type.fromjson(value.get_dict_value('note'))
        region = Region.fromjson(value.get_dict_value('at'))
        content = value.get_dict_value('it')
        what = content.get_list_item(0).value_string()
        if what == 'BoolE':
            ast = BoolE.fromjson(content)
        elif what == 'NumE':
            ast = NumE.fromjson(content)
        elif what == 'TextE':
            ast = TextE.fromjson(content)
        elif what == 'VarE':
            ast = VarE.fromjson(content)
        elif what == 'UnE':
            ast = UnE.fromjson(content)
        elif what == 'BinE':
            ast = BinE.fromjson(content)
        elif what == 'CmpE':
            ast = CmpE.fromjson(content)
        elif what == 'UpCastE':
            ast = UpCastE.fromjson(content)
        elif what == 'DownCastE':
            ast = DownCastE.fromjson(content)
        elif what == 'SubE':
            ast = SubE.fromjson(content)
        elif what == 'MatchE':
            ast = MatchE.fromjson(content)
        elif what == 'TupleE':
            ast = TupleE.fromjson(content)
        elif what == 'CaseE':
            ast = CaseE.fromjson(content)
        elif what == 'StrE':
            ast = StrE.fromjson(content)
        elif what == 'OptE':
            ast = OptE.fromjson(content)
        elif what == 'ListE':
            ast = ListE.fromjson(content)
        elif what == 'ConsE':
            ast = ConsE.fromjson(content)
        elif what == 'CatE':
            ast = CatE.fromjson(content)
        elif what == 'MemE':
            ast = MemE.fromjson(content)
        elif what == 'LenE':
            ast = LenE.fromjson(content)
        elif what == 'DotE':
            ast = DotE.fromjson(content)
        elif what == 'IdxE':
            ast = IdxE.fromjson(content)
        elif what == 'SliceE':
            ast = SliceE.fromjson(content)
        elif what == 'UpdE':
            ast = UpdE.fromjson(content)
        elif what == 'CallE':
            ast = CallE.fromjson(content)
        elif what == 'IterE':
            ast = IterE.fromjson(content)
        else:
            raise P4UnknownTypeError("Unknown Exp type: %s" % what)
        ast.typ = typ
        ast.region = region
        return ast

    def tostring(self):
        assert 0


class BoolE(Exp):
    _attrs_ = ['value']
    def __init__(self, value):
        assert isinstance(value, bool)
        self.value = value # type: bool

    @staticmethod
    def fromjson(content):
        return BoolE(
            value=content.get_list_item(1).value_bool()
        )

    def __repr__(self):
        return "p4specast.BoolE(%r)" % (self.value,)

    def tostring(self):
        # | Il.Ast.BoolE b -> string_of_bool b
        return "true" if self.value else "false"


class NumE(Exp):
    def __init__(self, value, what, typ=None):
        self.value = value # type: integers.Integer
        self.what = what # type: IntType
        self.typ = typ # type: Type

    @staticmethod
    def fromjson(content):
        what = content.get_list_item(1).get_list_item(0).value_string()
        if what == 'Int':
            what = IntT.INSTANCE
        else:
            assert what == 'Nat'
            what = NatT.INSTANCE
        return NumE.fromstr(content.get_list_item(1).get_list_item(1).value_string(), what)

    @staticmethod
    def fromstr(valuestr, what, typ=None):
        return NumE(integers.Integer.fromstr(valuestr),
                    what, typ)

    def __repr__(self):
        return "p4specast.NumE.fromstr(%r, %r)" % (self.value.str(), self.what)

    def tostring(self):
        # | Il.Ast.NumE n -> string_of_num n
        return self.value.str()


class TextE(Exp):
    def __init__(self, value):
        self.value = value # typ: str

    @staticmethod
    def fromjson(content):
        return TextE(
            value=content.get_list_item(1).value_string()
        )

    def __repr__(self):
        return "p4specast.TextE(%r)" % (self.value,)

    def tostring(self):
        # | Il.Ast.TextE text -> "\"" ^ String.escaped text ^ "\""
        from rpyp4sp.objects import string_escape_encode
        return string_escape_encode(self.value)

class VarE(Exp):
    def __init__(self, id):
        self.id = id # typ: id

    @staticmethod
    def fromjson(content):
        return VarE(
            id=Id.fromjson(content.get_list_item(1))
        )

    def __repr__(self):
        return "p4specast.VarE(%r)" % (self.id,)

    def tostring(self):
        # | Il.Ast.VarE varid -> string_of_varid varid
        return self.id.value

class UnE(Exp):
    #   | UnE of unop * optyp * exp             (* unop exp *)
    def __init__(self, op, optyp, exp):
        self.op = op # typ: unop
        self.optyp = optyp # typ: optyp
        self.exp = exp # typ: Exp

    def __repr__(self):
        return "p4specast.UnE(%r, %r, %r)" % (self.op, self.optyp, self.exp)

    def tostring(self):
        # | Il.Ast.UnE (unop, _, exp) -> string_of_unop unop ^ string_of_exp exp
        # let string_of_unop = function `NotOp -> "~" | `PlusOp -> "+" | `MinusOp -> "-"
        if self.op == "NotOp":
            unop_str = "~"
        elif self.op == "PlusOp":
            unop_str = "+"
        elif self.op == "MinusOp":
            unop_str = "-"
        else:
            unop_str = "?%s?" % self.op  # fallback for unknown ops
        return "%s%s" % (unop_str, self.exp.tostring())

    @staticmethod
    def fromjson(content):
        return UnE(
            op=content.get_list_item(1).get_list_item(0).value_string(),
            optyp=content.get_list_item(2).get_list_item(0).value_string(),
            exp=Exp.fromjson(content.get_list_item(3))
        )

class BinE(Exp):
    #   | BinE of binop * optyp * exp * exp     (* exp binop exp *)
    def __init__(self, binop, optyp, left, right):
        self.binop = binop # typ: binop
        self.optyp = optyp # typ: optyp
        self.left = left # typ: Exp
        self.right = right # typ: Exp

    def __repr__(self):
        return "p4specast.BinE(%r, %r, %r, %r)" % (self.binop, self.optyp, self.left, self.right)

    def tostring(self):
        # | Il.Ast.BinE (binop, _, exp_l, exp_r) ->
        #     "(" ^ string_of_exp exp_l ^ " " ^ string_of_binop binop ^ " "
        #     ^ string_of_exp exp_r ^ ")"
        # let string_of_binop = function
        #   | `AndOp -> "/\\" | `OrOp -> "\\/" | `ImplOp -> "=>" | `EquivOp -> "<=>"
        #   | `AddOp -> "+" | `SubOp -> "-" | `MulOp -> "*" | `DivOp -> "/" | `ModOp -> "\\" | `PowOp -> "^"
        binop_map = {
            "AndOp": "/\\",
            "OrOp": "\\/",
            "ImplOp": "=>",
            "EquivOp": "<=>",
            "AddOp": "+",
            "SubOp": "-",
            "MulOp": "*",
            "DivOp": "/",
            "ModOp": "\\",
            "PowOp": "^"
        }
        binop_str = binop_map.get(self.binop, "?%s?" % self.binop)
        return "(%s %s %s)" % (self.left.tostring(), binop_str, self.right.tostring())

    @staticmethod
    def fromjson(content):
        return BinE(
            binop=content.get_list_item(1).get_list_item(0).value_string(),
            optyp=content.get_list_item(2).get_list_item(0).value_string(),
            left=Exp.fromjson(content.get_list_item(3)),
            right=Exp.fromjson(content.get_list_item(4))
        )

class CmpE(Exp):
#   | CmpE of cmpop * optyp * exp * exp     (* exp cmpop exp *)
    def __init__(self, cmpop, optyp, left, right):
        self.cmpop = cmpop # typ: cmpop
        self.optyp = optyp # typ: optyp
        self.left = left # typ: Exp
        self.right = right # typ: Exp

    def __repr__(self):
        return "p4specast.CmpE(%r, %r, %r, %r)" % (self.cmpop, self.optyp, self.left, self.right)

    def tostring(self):
        # | Il.Ast.CmpE (cmpop, _, exp_l, exp_r) ->
        #     "(" ^ string_of_exp exp_l ^ " " ^ string_of_cmpop cmpop ^ " "
        #     ^ string_of_exp exp_r ^ ")"
        # let string_of_cmpop = function
        #   | `EqOp -> "=" | `NeOp -> "=/=" | `LtOp -> "<" | `GtOp -> ">" | `LeOp -> "<=" | `GeOp -> ">="
        cmpop_map = {
            "EqOp": "=",
            "NeOp": "=/=",
            "LtOp": "<",
            "GtOp": ">",
            "LeOp": "<=",
            "GeOp": ">="
        }
        cmpop_str = cmpop_map.get(self.cmpop, "?%s?" % self.cmpop)
        return "(%s %s %s)" % (self.left.tostring(), cmpop_str, self.right.tostring())

    @staticmethod
    def fromjson(content):
        return CmpE(
            cmpop=content.get_list_item(1).get_list_item(0).value_string(),
            optyp=content.get_list_item(2).get_list_item(0).value_string(),
            left=Exp.fromjson(content.get_list_item(3)),
            right=Exp.fromjson(content.get_list_item(4))
        )

class UpCastE(Exp):
#   | UpCastE of typ * exp                  (* exp as typ *)
    def __init__(self, check_typ, exp):
        self.check_typ = check_typ # typ: Typ
        self.exp = exp # typ: Exp

    def tostring(self):
        # | Il.Ast.UpCastE (e, t) -> string_of_exp e ^ " : " ^ string_of_typ t
        return "%s : %s" % (self.exp.tostring(), self.check_typ.tostring())

    def __repr__(self):
        return "p4specast.UpCastE(%r, %r)" % (self.check_typ, self.exp)

    @staticmethod
    def fromjson(content):
        return UpCastE(
            check_typ=Type.fromjson(content.get_list_item(1)),
            exp=Exp.fromjson(content.get_list_item(2)),
        )

class DownCastE(Exp):
#   | DownCastE of typ * exp                (* exp as typ *)
    def __init__(self, check_typ, exp):
        self.check_typ = check_typ # typ: typ
        self.exp = exp # typ: exp

    def tostring(self):
        # | Il.Ast.DownCastE (e, t) -> string_of_exp e ^ " as " ^ string_of_typ t
        return "%s as %s" % (self.exp.tostring(), self.check_typ.tostring())

    def __repr__(self):
        return "p4specast.DownCastE(%r, %r)" % (self.check_typ, self.exp)

    @staticmethod
    def fromjson(content):
        return DownCastE(
            check_typ=Type.fromjson(content.get_list_item(1)),
            exp=Exp.fromjson(content.get_list_item(2)),
        )

class SubE(Exp):
#   | SubE of exp * typ                     (* exp `<:` typ *)
    def __init__(self, exp, check_typ):
        self.exp = exp
        self.check_typ = check_typ

    def tostring(self):
        # | Il.Ast.SubE (e, _, ds) -> string_of_exp e ^ " with " ^ concat_map_nl "\n  " string_of_defn ds
        return "%s <: %s" % (self.exp.tostring(), self.check_typ.tostring())

    @staticmethod
    def fromjson(content):
        return SubE(
            exp=Exp.fromjson(content.get_list_item(1)),
            check_typ=Type.fromjson(content.get_list_item(2))
        )

    def __repr__(self):
        return "p4specast.SubE(%r, %r)" % (self.exp, self.check_typ)

class MatchE(Exp):
#   | MatchE of exp * pattern               (* exp `matches` pattern *)
    def __init__(self, exp, pattern):
        self.exp = exp
        self.pattern = pattern

    def tostring(self):
        # | Il.Ast.MatchE (e, cs) -> "match " ^ string_of_exp e ^ " with" ^ concat_map_nl "\n  | " string_of_clause cs
        return "%s matches %s" % (self.exp.tostring(), self.pattern.tostring())

    @staticmethod
    def fromjson(content):
        return MatchE(
            exp=Exp.fromjson(content.get_list_item(1)),
            pattern=Pattern.fromjson(content.get_list_item(2))
        )

    def __repr__(self):
        return "p4specast.MatchE(%r, %r)" % (self.exp, self.pattern)

class TupleE(Exp):
#   | TupleE of exp list                    (* `(` exp* `)` *)
    def __init__(self, elts):
        self.elts = elts # typ: exp list

    def tostring(self):
        # | Il.Ast.TupleE es -> "(" ^ concat_map ", " string_of_exp es ^ ")"
        elts_str = ", ".join([e.tostring() for e in self.elts])
        return "(%s)" % elts_str

    @staticmethod
    def fromjson(content):
        return TupleE(
            elts=[Exp.fromjson(elt) for elt in content.get_list_item(1).value_array()]
        )

    def __repr__(self):
        return "p4specast.TupleE(%r)" % (self.elts,)

class CaseE(Exp):
#   | CaseE of notexp                       (* notexp *)
    def __init__(self, notexp):
        self.notexp = notexp

    def tostring(self):
        # | Il.Ast.CaseE (op, es) -> string_of_mixop_with_exp op es
        return self.notexp.tostring()

    @staticmethod
    def fromjson(content):
        return CaseE(
            notexp=NotExp.fromjson(content.get_list_item(1))
        )

    def __repr__(self):
        return "p4specast.CaseE(%r)" % (self.notexp,)

class StrE(Exp):
#   | StrE of (atom * exp) list             (* { expfield* } *)
    def __init__(self, fields):
        self.fields = fields

    def tostring(self):
        # | Il.Ast.StrE efs -> "{" ^ concat_map "; " string_of_expfield efs ^ "}"
        fields_str = "; ".join(["%s %s" % (field[0].tostring(), field[1].tostring()) for field in self.fields])
        return "{%s}" % fields_str

    @staticmethod
    def fromjson(content):
        return StrE(
            fields=[(AtomT.fromjson(field.get_list_item(0)), Exp.fromjson(field.get_list_item(1))) for field in content.get_list_item(1).value_array()]
        )

    def __repr__(self):
        return "p4specast.StrE(%r)" % (self.fields,)

class OptE(Exp):
#   | OptE of exp option                    (* exp? *)
    def __init__(self, exp):
        self.exp = exp # typ: Exp | None

    def tostring(self):
        # | Il.Ast.OptE eo -> (match eo with None -> "" | Some e -> string_of_exp e ^ "?")
        if self.exp is None:
            return ""
        return "%s?" % self.exp.tostring()

    @staticmethod
    def fromjson(content):
        if content.get_list_item(1).is_null:
            return OptE(exp=None)
        return OptE(
            exp=Exp.fromjson(content.get_list_item(1))
        )

    def __repr__(self):
        return "p4specast.OptE(%r)" % (self.exp,)

class ListE(Exp):
#   | ListE of exp list                     (* `[` exp* `]` *)
    def __init__(self, elts):
        self.elts = elts # typ: exp list

    def tostring(self):
        # | Il.Ast.ListE es -> "[" ^ concat_map "; " string_of_exp es ^ "]"
        elts_str = "; ".join([e.tostring() for e in self.elts])
        return "[%s]" % elts_str

    @staticmethod
    def fromjson(content):
        return ListE(
            elts=[Exp.fromjson(elt) for elt in content.get_list_item(1).value_array()]
        )

    def __repr__(self):
        return "p4specast.ListE(%r)" % (self.elts,)

class ConsE(Exp):
#   | ConsE of exp * exp                    (* exp `::` exp *)
    def __init__(self, head, tail):
        self.head = head # typ: exp
        self.tail = tail # typ: exp

    def tostring(self):
        # | Il.Ast.ConsE (e1, e2) -> string_of_exp e1 ^ " :: " ^ string_of_exp e2
        return "%s :: %s" % (self.head.tostring(), self.tail.tostring())

    @staticmethod
    def fromjson(content):
        return ConsE(
            head=Exp.fromjson(content.get_list_item(1)),
            tail=Exp.fromjson(content.get_list_item(2))
        )

    def __repr__(self):
        return "p4specast.ConsE(%r, %r)" % (self.head, self.tail)

class CatE(Exp):
#   | CatE of exp * exp                     (* exp `++` exp *)
    def __init__(self, left, right):
        self.left = left # typ: exp
        self.right = right # typ: exp

    def tostring(self):
        # | Il.Ast.CatE (e1, e2) -> string_of_exp e1 ^ " ++ " ^ string_of_exp e2
        return "%s ++ %s" % (self.left.tostring(), self.right.tostring())

    @staticmethod
    def fromjson(content):
        return CatE(
            left=Exp.fromjson(content.get_list_item(1)),
            right=Exp.fromjson(content.get_list_item(2))
        )

    def __repr__(self):
        return "p4specast.CatE(%r, %r)" % (self.left, self.right)

class MemE(Exp):
#   | MemE of exp * exp                     (* exp `<-` exp *)
    def __init__(self, elem, lst):
        self.elem = elem # typ: exp
        self.lst = lst # typ: exp

    def tostring(self):
        # | Il.Ast.MemE (e1, e2) -> string_of_exp e1 ^ " <- " ^ string_of_exp e2
        return "%s <- %s" % (self.elem.tostring(), self.lst.tostring())

    @staticmethod
    def fromjson(content):
        return MemE(
            elem=Exp.fromjson(content.get_list_item(1)),
            lst=Exp.fromjson(content.get_list_item(2))
        )

    def __repr__(self):
        return "p4specast.MemE(%r, %r)" % (self.elem, self.lst)

class LenE(Exp):
#   | LenE of exp                           (* `|` exp `|` *)
    def __init__(self, lst):
        self.lst = lst # typ: exp

    def tostring(self):
        # | Il.Ast.LenE e -> "|" ^ string_of_exp e ^ "|"
        return "|%s|" % self.lst.tostring()

    @staticmethod
    def fromjson(content):
        return LenE(
            lst=Exp.fromjson(content.get_list_item(1))
        )

    def __repr__(self):
        return "p4specast.LenE(%r)" % (self.lst,)

class DotE(Exp):
#   | DotE of exp * atom                    (* exp.atom *)
    def __init__(self, obj, field):
        self.obj = obj # typ: exp
        self.field = field # typ: string

    def tostring(self):
        # | Il.Ast.DotE (e, atom) -> string_of_exp e ^ "." ^ string_of_atom atom
        return "%s.%s" % (self.obj.tostring(), self.field.tostring())

    @staticmethod
    def fromjson(content):
        return DotE(
            obj=Exp.fromjson(content.get_list_item(1)),
            field=AtomT.fromjson(content.get_list_item(2))
        )

    def __repr__(self):
        return "p4specast.DotE(%r, %r)" % (self.obj, self.field)

class IdxE(Exp):
#   | IdxE of exp * exp                     (* exp `[` exp `]` *)
    def __init__(self, lst, idx):
        self.lst = lst # typ: exp
        self.idx = idx # typ: exp

    def tostring(self):
        # | Il.Ast.IdxE (e1, e2) -> string_of_exp e1 ^ "[" ^ string_of_exp e2 ^ "]"
        return "%s[%s]" % (self.lst.tostring(), self.idx.tostring())

    @staticmethod
    def fromjson(content):
        return IdxE(
            lst=Exp.fromjson(content.get_list_item(1)),
            idx=Exp.fromjson(content.get_list_item(2))
        )

    def __repr__(self):
        return "p4specast.IdxE(%r, %r)" % (self.lst, self.idx)

class SliceE(Exp):
#   | SliceE of exp * exp * exp             (* exp `[` exp `:` exp `]` *)
    def __init__(self, lst, start, length):
        self.lst = lst # typ: exp
        self.start = start # typ: exp
        self.length = length # typ: exp

    def tostring(self):
        # | Il.Ast.SliceE (e1, e2, e3) -> string_of_exp e1 ^ "[" ^ string_of_exp e2 ^ " : " ^ string_of_exp e3 ^ "]"
        return "%s[%s : %s]" % (self.lst.tostring(), self.start.tostring(), self.length.tostring())

    @staticmethod
    def fromjson(content):
        return SliceE(
            lst=Exp.fromjson(content.get_list_item(1)),
            start=Exp.fromjson(content.get_list_item(2)),
            length=Exp.fromjson(content.get_list_item(3))
        )

    def __repr__(self):
        return "p4specast.SliceE(%r, %r, %r)" % (self.lst, self.start, self.length)

class UpdE(Exp):
#   | UpdE of exp * path * exp              (* exp `[` path `=` exp `]` *)
    def __init__(self, exp, path, value):
        self.exp = exp
        self.path = path
        self.value = value

    def tostring(self):
        # | Il.Ast.UpdE (e1, p, e2) -> string_of_exp e1 ^ "[" ^ string_of_path p ^ " = " ^ string_of_exp e2 ^ "]"
        return "%s[%s = %s]" % (self.exp.tostring(), self.path.tostring(), self.value.tostring())  # TODO: implement Path.tostring

    @staticmethod
    def fromjson(content):
        return UpdE(
            exp=Exp.fromjson(content.get_list_item(1)),
            path=Path.fromjson(content.get_list_item(2)),
            value=Exp.fromjson(content.get_list_item(3))
        )

    def __repr__(self):
        return "p4specast.UpdE(%r, %r, %r)" % (self.exp, self.path, self.value)

class CallE(Exp):
#   | CallE of id * targ list * arg list    (* $id`<` targ* `>``(` arg* `)` *)
    def __init__(self, func, targs, args):
        self.func = func # typ: Id
        self.targs = targs
        self.args = args # typ: exp list

    def tostring(self):
        # | Il.Ast.CallE (f, ts, as_) -> "$" ^ string_of_varid f ^ string_of_list_nl string_of_targ_inl ts ^ "(" ^ concat_map ", " string_of_arg as_ ^ ")"
        targs_str = ""
        if self.targs:
            targs_str = "<%s>" % ", ".join([t.tostring() for t in self.targs])
        args_str = ", ".join([a.tostring() for a in self.args])
        return "$%s%s(%s)" % (self.func.value, targs_str, args_str)

    @staticmethod
    def fromjson(content):
        return CallE(
            func=Id.fromjson(content.get_list_item(1)),
            targs=[Type.fromjson(targ) for targ in content.get_list_item(2).value_array()],
            args=[Arg.fromjson(arg) for arg in content.get_list_item(3).value_array()]
        )

    def __repr__(self):
        return "p4specast.CallE(%r, %r, %r)" % (self.func, self.targs, self.args)


class IterE(Exp):
#   | IterE of exp * iterexp                (* exp iterexp *)
# iterexp = iter * var list
    def __init__(self, exp, iter, varlist):
        self.exp = exp
        self.iter = iter
        self.varlist = varlist

    def tostring(self):
        # | Il.Ast.IterE (e, (iter, xs)) -> "(" ^ string_of_exp e ^ " " ^ string_of_iter iter ^ concat_map " " string_of_varid xs ^ ")"
        vars_str = " ".join([v.tostring() for v in self.varlist])  # TODO: implement Var.tostring
        return "(%s %s %s)" % (self.exp.tostring(), string_of_iter(self.iter), vars_str)

    def __repr__(self):
        return "p4specast.IterE(%r, %r, %r)" % (self.exp, self.iter, self.varlist)

    @staticmethod
    def fromjson(content):
        return IterE(
            exp=Exp.fromjson(content.get_list_item(1)),
            iter=Iter.fromjson(content.get_list_item(2).get_list_item(0)),
            varlist=[Var.fromjson(value) for value in content.get_list_item(2).get_list_item(1).value_array()],
        )

# and notexp = mixop * exp list

class NotExp(AstBase):
    def __init__(self, mixop, exps):
        self.mixop = mixop
        self.exps = exps

    def tostring(self, typ=None):
        # and string_of_notexp ?(typ = None) notexp =
        #   let mixop, exps = notexp in
        #   match typ with
        #   | Some typ ->
        #       string_of_mixop mixop ^ "_"
        #       ^ string_of_typ (typ $ no_region)
        #       ^ "(" ^ string_of_exps ", " exps ^ ")"
        #   | None -> string_of_mixop mixop ^ "(" ^ string_of_exps ", " exps ^ ")"
        exps_str = ", ".join([e.tostring() for e in self.exps])
        if typ is not None:
            return "%s_%s(%s)" % (self.mixop.tostring(), typ.tostring(), exps_str)
        else:
            return "%s(%s)" % (self.mixop.tostring(), exps_str)

    @staticmethod
    def fromjson(content):
        return NotExp(
            mixop=MixOp.fromjson(content.get_list_item(0)),
            exps=[Exp.fromjson(exp) for exp in content.get_list_item(1).value_array()]
        )
    def __repr__(self):
        return "p4specast.NotExp(%r, %r)" % (self.mixop, self.exps)

# and iterexp = iter * var list

class IterExp(AstBase):
    def __init__(self, iter, vars):
        self.iter = iter
        self.vars = vars

    def tostring(self):
        # and string_of_iterexp iterexp =
        #   let iter, vars = iterexp in
        #   string_of_iter iter ^ "{"
        #   ^ String.concat ", "
        #       (List.map
        #          (fun var ->
        #            let id, typ, iters = var in
        #            string_of_var var ^ " <- " ^ string_of_var (id, typ, iters @ [ iter ]))
        #          vars)
        #   ^ "}"
        res = [string_of_iter(self.iter)]
        res.append("{")
        var_strs = []
        for var in self.vars:
            id, typ, iters = var.id, var.typ, var.iter
            var_strs.append("%s <- %s" % (var.tostring(), Var(id, typ, iters + [self.iter]).tostring()))
        res.append(", ".join(var_strs))
        res.append("}")
        return "".join(res)

    @staticmethod
    def fromjson(content):
        return IterExp(
            iter=Iter.fromjson(content.get_list_item(0)),
            vars=[Var.fromjson(var) for var in content.get_list_item(1).value_array()]
        )

    def __repr__(self):
        return "p4specast.IterExp(%r, %r)" % (self.iter, self.vars)

# _________________________________________________________________


# type typ = [ `NatT | `IntT ] [@@deriving yojson]

NumTyp, NatT, IntT = define_enum('NumTyp', 'NatT', 'IntT')

# types
#   | NumT of Num.typ         (* numtyp *)
#   | TextT                   (* `text` *)
#   | VarT of id * targ list  (* id (`<` list(targ, `,`) `>`)? *)
#   | TupleT of typ list      (* `(` list(typ, `,`) `)` *)
#   | IterT of typ * iter     (* typ iter *)
#   | FuncT                   (* `func` *)

class Type(AstBase):
    # has a .region, but only sometimes (eg exp uses typ')

    _attr_ = ['region', '_iterlist', '_iteropt']
    _iterlist = None
    _iteropt = None

    def tostring(self):
        assert 0  # abstract method

    def tojson(self):
        from rpyp4sp import rpyjson
        content = self._tojson_content()
        if not hasattr(self, 'region') or self.region is None:
            return rpyjson.JsonArray(content)
        else:
            root_map = rpyjson.ROOT_MAP.get_next("at").get_next("it")
            return rpyjson.JsonObject2(root_map, self.region.tojson(), rpyjson.JsonArray(content))

    def _tojson_content(self):
        assert 0  # abstract method

    @staticmethod
    def fromjson(value):
        if value.is_object:
            region = Region.fromjson(value.get_dict_value('at'))
            content = value.get_dict_value('it')
        else:
            region = None
            content = value
        what = content.get_list_item(0).value_string()
        if what == 'BoolT':
            ast = BoolT.fromjson(content)
        elif what == 'NumT':
            ast = NumT.fromjson(content)
        elif what == 'TextT':
            ast = TextT.fromjson(content)
        elif what == 'VarT':
            ast = VarT.fromjson(content)
        elif what == 'TupleT':
            ast = TupleT.fromjson(content)
        elif what == 'IterT':
            ast = IterT.fromjson(content)
        elif what == 'FuncT':
            ast = FuncT.fromjson(content)
        else:
            raise P4UnknownTypeError("Unknown Type: %s" % what)
        ast.region = region
        return ast

    @jit.elidable
    def list_of(self):
        if self._iterlist is not None:
            return self._iterlist
        self._iterlist = res = IterT(self, List.INSTANCE)
        res.region = NO_REGION
        return res

    @jit.elidable
    def opt_of(self):
        if self._iteropt is not None:
            return self._iteropt
        self._iteropt = res = IterT(self, Opt.INSTANCE)
        res.region = NO_REGION
        return res


class BoolT(Type):
    def __init__(self):
        pass

    def tostring(self):
        # | BoolT -> "bool"
        return "bool"

    def __repr__(self):
        return "p4specast.BoolT.INSTANCE"

    def _tojson_content(self):
        from rpyp4sp import rpyjson
        return [rpyjson.JsonString("BoolT")]

    @staticmethod
    def fromjson(content):
        return BoolT.INSTANCE
BoolT.INSTANCE = BoolT()


class NumT(Type):
    def __init__(self, typ):
        self.typ = typ # type: NumTyp

    def tostring(self):
        # | NumT numtyp -> Num.string_of_typ numtyp
        if isinstance(self.typ, NatT):
            return 'nat'
        if isinstance(self.typ, IntT):
            return 'int'
        assert 0, 'unreachable'

    def __repr__(self):
        if isinstance(self.typ, IntT):
            return "p4specast.NumT.INT"
        elif isinstance(self.typ, NatT):
            return "p4specast.NumT.NAT"
        else:
            return "p4specast.NumT(%r)" % (self.typ,)

    def _tojson_content(self):
        from rpyp4sp import rpyjson
        return [rpyjson.JsonString("NumT"), self.typ.tojson()]

    @staticmethod
    def fromjson(content):
        typ = NumTyp.fromjson(content.get_list_item(1))
        if isinstance(typ, IntT):
            return NumT.INT
        elif isinstance(typ, NatT):
            return NumT.NAT
        else:
            return NumT(typ)
NumT.INT = NumT(IntT.INSTANCE)
NumT.NAT = NumT(NatT.INSTANCE)



class TextT(Type):
    def __init__(self):
        pass

    def tostring(self):
        # | TextT -> "text"
        return "text"

    def __repr__(self):
        return "p4specast.TextT.INSTANCE"

    def _tojson_content(self):
        from rpyp4sp import rpyjson
        return [rpyjson.JsonString("TextT")]

    @staticmethod
    def fromjson(content):
        return TextT.INSTANCE

class VarT(Type):
    def __init__(self, id, targs):
        self.id = id
        self.targs = targs

    def tostring(self):
        # | VarT (typid, targs) -> string_of_typid typid ^ string_of_targs targs
        targs_str = ""
        if self.targs:
            targs_str = "<%s>" % ", ".join([t.tostring() for t in self.targs])
        return "%s%s" % (self.id.value, targs_str)

    def __repr__(self):
        return "p4specast.VarT(%r, %r)" % (self.id, self.targs)

    def _tojson_content(self):
        from rpyp4sp import rpyjson
        targs_json = [targ.tojson() for targ in self.targs]
        return [rpyjson.JsonString("VarT"), self.id.tojson(), rpyjson.JsonArray(targs_json)]

    @staticmethod
    def fromjson(content):
        return VarT(
            id=Id.fromjson(content.get_list_item(1)),
            targs=[Type.fromjson(targ) for targ in content.get_list_item(2).value_array()]
        )

class TupleT(Type):
    def __init__(self, elts):
        self.elts = elts

    def tostring(self):
        # | TupleT typs -> "(" ^ string_of_typs ", " typs ^ ")"
        elts_str = ", ".join([e.tostring() for e in self.elts])
        return "(%s)" % elts_str

    def __repr__(self):
        return "p4specast.TupleT(%r)" % (self.elts,)

    def _tojson_content(self):
        from rpyp4sp import rpyjson
        elts_json = [elt.tojson() for elt in self.elts]
        return [rpyjson.JsonString("TupleT"), rpyjson.JsonArray(elts_json)]

    @staticmethod
    def fromjson(content):
        return TupleT(
            elts=[Type.fromjson(elt) for elt in content.get_list_item(1).value_array()]
        )

class IterT(Type):
    def __init__(self, typ, iter):
        self.typ = typ
        self.iter = iter

    def tostring(self):
        # | IterT (typ, iter) -> string_of_typ typ ^ string_of_iter iter
        return "%s%s" % (self.typ.tostring(), string_of_iter(self.iter))

    def __repr__(self):
        return "p4specast.IterT(%r, %r)" % (self.typ, self.iter)

    def _tojson_content(self):
        from rpyp4sp import rpyjson
        return [rpyjson.JsonString("IterT"), self.typ.tojson(), self.iter.tojson()]

    @staticmethod
    def fromjson(content):
        return IterT(
            typ=Type.fromjson(content.get_list_item(1)),
            iter=Iter.fromjson(content.get_list_item(2)),
        )

class FuncT(Type):
    def __init__(self):
        pass

    def tostring(self):
        # | FuncT -> "func"
        return "func"

    def __repr__(self):
        return "p4specast.FuncT.INSTANCE"

    def _tojson_content(self):
        from rpyp4sp import rpyjson
        return [rpyjson.JsonString("FuncT")]

    @staticmethod
    def fromjson(content):
        return FuncT.INSTANCE

TextT.INSTANCE = TextT()
FuncT.INSTANCE = FuncT()

# and nottyp = nottyp' phrase
# [@@deriving yojson]
# and nottyp' = mixop * typ list
# [@@deriving yojson]

class NotTyp(AstBase):
    def __init__(self, mixop, typs):
        self.mixop = mixop
        self.typs = typs

    def tostring(self):
        # and string_of_nottyp nottyp =
        #   let mixop, typs = nottyp.it in
        #   string_of_mixop mixop ^ "(" ^ string_of_typs ", " typs ^ ")"
        typs_str = ", ".join([t.tostring() for t in self.typs])
        return "%s(%s)" % (self.mixop.tostring(), typs_str)

    def __repr__(self):
        return "p4specast.NotTyp(%r, %r)" % (self.mixop, self.typs)

    @staticmethod
    def fromjson(value):
        region = Region.fromjson(value.get_dict_value('at'))
        content = value.get_dict_value('it')
        return NotTyp(
            mixop=MixOp.fromjson(content.get_list_item(0)),
            typs=[Type.fromjson(typ) for typ in content.get_list_item(1).value_array()]
        )

# and deftyp = deftyp' phrase
# and deftyp' =
#   | PlainT of typ
#   | StructT of typfield list
#   | VariantT of typcase list

class DefTyp(AstBase):
    # base class
    @staticmethod
    def fromjson(value):
        region = Region.fromjson(value.get_dict_value('at'))
        content = value.get_dict_value('it')
        what = content.get_list_item(0).value_string()
        if what == 'PlainT':
            ast = PlainT.fromjson(content)
        elif what == 'StructT':
            ast = StructT.fromjson(content)
        elif what == 'VariantT':
            ast = VariantT.fromjson(content)
        else:
            raise P4UnknownTypeError("Unknown DefTyp: %s" % what)
        ast.region = region
        return ast

class PlainT(DefTyp):
    def __init__(self, typ, region=None):
        self.typ = typ
        self.region = region

    @staticmethod
    def fromjson(content):
        return PlainT(
            typ=Type.fromjson(content.get_list_item(1))
        )

    def __repr__(self):
        return "p4specast.PlainT(typ=%s)" % (self.typ,)

class StructT(DefTyp):
    def __init__(self, fields):
        self.fields = fields

    @staticmethod
    def fromjson(content):
        return StructT(
            fields=[TypField.fromjson(field) for field in content.get_list_item(1).value_array()]
        )

    def __repr__(self):
        return "p4specast.StructT(fields=%s)" % (self.fields,)

class VariantT(DefTyp):
    def __init__(self, cases):
        self.cases = cases

    @staticmethod
    def fromjson(content):
        return VariantT(
            cases=[TypeCase.fromjson(case) for case in content.get_list_item(1).value_array()]
        )

    def __repr__(self):
        return "p4specast.VariantT(cases=%s)" % (self.cases,)

# and typfield = atom * typ

class TypField(AstBase):
    def __init__(self, name, typ):
        self.name = name
        self.typ = typ

    def __repr__(self):
        return "p4specast.TypField(%r, %r)" % (self.name, self.typ)

    @staticmethod
    def fromjson(content):
        return TypField(
            name=AtomT.fromjson(content.get_list_item(0)),
            typ=Type.fromjson(content.get_list_item(1))
        )

# and typcase = nottyp

TypeCase = NotTyp

# _____________________________________
# instrs

# and instr = instr' phrase [@@deriving yojson]
# and instr' =
#   | IfI of exp * iterexp list * instr list * phantom option
#   | HoldI of id * notexp * iterexp list * holdcase
#   | CaseI of exp * case list * phantom option
#   | OtherwiseI of instr
#   | LetI of exp * exp * iterexp list
#   | RuleI of id * notexp * iterexp list
#   | ResultI of exp list
#   | ReturnI of exp

class Instr(AstBase):
    _attrs_ = ['region']
    # has a .region

    def tostring(self, level=0, index=0):
        assert 0  # abstract method

    @staticmethod
    def fromjson(value):
        assert value.get_dict_value('note').is_null
        region = Region.fromjson(value.get_dict_value('at'))
        content = value.get_dict_value('it')
        what = content.get_list_item(0).value_string()
        if what == 'IfI':
            ast = IfI.fromjson(content)
        elif what == 'HoldI':
            ast = HoldI.fromjson(content)
        elif what == 'CaseI':
            ast = CaseI.fromjson(content)
        elif what == 'OtherwiseI':
            ast = OtherwiseI.fromjson(content)
        elif what == 'LetI':
            ast = LetI.fromjson(content)
        elif what == 'RuleI':
            ast = RuleI.fromjson(content)
        elif what == 'ResultI':
            ast = ResultI.fromjson(content)
        elif what == 'ReturnI':
            ast = ReturnI.fromjson(content)
        else:
            raise P4UnknownTypeError("Unknown Instr: %s" % what)
        ast.region = region
        return ast


class InstrWithIters(Instr):
    _attrs_ = ['iters', '_reverse_iters']
    _immutable_fields_ = ['iters[*]']

    _reverse_iters = None

    def _get_reverse_iters(self):
        if self._reverse_iters is not None:
            return self._reverse_iters
        res = ReverseIterExp.from_unreversed_list(self.iters)
        self._reverse_iters = res
        return res


class IfI(InstrWithIters):
    def __init__(self, exp, iters, instrs, phantom, region=None):
        self.exp = exp
        self.iters = iters
        self.instrs = instrs
        self.phantom = phantom
        self.region = region

    def tostring(self, level=0, index=0):
        # | IfI (exp_cond, iterexps, instrs_then, None) ->
        #     Format.asprintf "%sIf (%s)%s, then\n\n%s" order (string_of_exp exp_cond)
        #       (string_of_iterexps iterexps)
        #       (string_of_instrs ~level:(level + 1) instrs_then)
        # | IfI (exp_cond, iterexps, instrs_then, Some phantom) ->
        #     Format.asprintf "%sIf (%s)%s, then\n\n%s\n\n%sElse %s" order
        #       (string_of_exp exp_cond) (string_of_iterexps iterexps)
        #       (string_of_instrs ~level:(level + 1) instrs_then) order (string_of_phantom phantom)
        indent = "  " * level
        order = "%s%d. " % (indent, index)
        iterexps_str = string_of_iterexps(self.iters)
        instrs_str = string_of_instrs(self.instrs, level + 1)

        if self.phantom is None:  # None case
            return "%sIf (%s)%s, then\n\n%s" % (order, self.exp.tostring(), iterexps_str, instrs_str)
        else:  # Some phantom case
            phantom_str = self.phantom.tostring()
            return "%sIf (%s)%s, then\n\n%s\n\n%sElse %s" % (order, self.exp.tostring(), iterexps_str, instrs_str, order, phantom_str)

    @staticmethod
    def fromjson(content):
        return IfI(
            exp=Exp.fromjson(content.get_list_item(1)),
            iters=[IterExp.fromjson(ite) for ite in content.get_list_item(2).value_array()],
            instrs=[Instr.fromjson(instr) for instr in content.get_list_item(3).value_array()],
            phantom=Phantom.fromjson(content.get_list_item(4)),
        )

    def __repr__(self):
        return "p4specast.IfI(%r, %r, %r, %r%s)" % (self.exp, self.iters, self.instrs, self.phantom, (", " + repr(self.region)) if self.region is not None else '')


class HoldI(InstrWithIters):
    _immutable_fields_ = ['id', 'notexp']

#   | HoldI of id * notexp * iterexp list * holdcase
    def __init__(self, id, notexp, iters, holdcase, region=None):
        self.id = id
        self.notexp = notexp
        self.iters = iters
        self.holdcase = holdcase
        self.region = region

    def tostring(self, level=0, index=0):
        # | HoldI (id, notexp, iterexps, holdcase) ->
        #     Format.asprintf "%sIf (%s: %s)%s:\n\n%s" order (string_of_relid id)
        #       (string_of_notexp notexp)
        #       (string_of_iterexps iterexps)
        #       (string_of_holdcase ~level:(level + 1) holdcase)
        indent = "  " * level
        order = "%s%d. " % (indent, index)
        iterexps_str = string_of_iterexps(self.iters)
        holdcase_str = self.holdcase.tostring(level + 1)
        return "%sIf (%s: %s)%s:\n\n%s" % (order, self.id.value, self.notexp.tostring(), iterexps_str, holdcase_str)

    @staticmethod
    def fromjson(content):
        return HoldI(
            id=Id.fromjson(content.get_list_item(1)),
            notexp=NotExp.fromjson(content.get_list_item(2)),
            iters=[IterExp.fromjson(ite) for ite in content.get_list_item(3).value_array()],
            holdcase=HoldCase.fromjson(content.get_list_item(4)),
        )

    def __repr__(self):
        return "p4specast.HoldI(%r, %r, %r, %r%s)" % (self.id, self.notexp, self.iters, self.holdcase, (", " + repr(self.region)) if self.region is not None else '')


class ReverseIterExp(object):
    def __init__(self, head, tail):
        self.head = head # type: IterExp
        self.tail = tail # type: ReverseIterExp

    @staticmethod
    def from_unreversed_list(l):
        next = None
        for el in l:
            next = ReverseIterExp(el, next)
        return next

    def __repr__(self):
        l = []
        while self:
            l.append(self.head)
            self = self.tail
        l.reverse()
        return "ReverseIterExp.from_unreversed_list(%r)" % (l, )


class CaseI(Instr):
    _immutable_fields_ = ['exp', 'cases[*]', 'cases_exps[*]']

    def __init__(self, exp, cases, phantom, region=None):
        self.exp = exp
        self.cases = cases
        self.phantom = phantom
        self.region = region
        self.cases_exps = [_combine_case_exp(exp, case) for case in cases]

    def tostring(self, level=0, index=0):
        # | CaseI (exp, cases, None) ->
        #     Format.asprintf "%sCase analysis on %s\n\n%s" order (string_of_exp exp)
        #       (string_of_cases ~level:(level + 1) cases)
        # | CaseI (exp, cases, Some phantom) ->
        #     Format.asprintf "%sCase analysis on %s\n\n%s\n\n%sElse %s" order
        #       (string_of_exp exp) (string_of_cases ~level:(level + 1) cases)
        #       order (string_of_phantom phantom)
        indent = "  " * level
        order = "%s%d. " % (indent, index)
        cases_str = string_of_cases(self.cases, level + 1)

        if self.phantom.is_null:  # None case
            return "%sCase analysis on %s\n\n%s" % (order, self.exp.tostring(), cases_str)
        else:  # Some phantom case
            phantom_str = self.phantom.tostring()
            return "%sCase analysis on %s\n\n%s\n\n%sElse %s" % (order, self.exp.tostring(), cases_str, order, phantom_str)

    @staticmethod
    def fromjson(content):
        return CaseI(
            exp=Exp.fromjson(content.get_list_item(1)),
            cases=[Case.fromjson(case) for case in content.get_list_item(2).value_array()],
            phantom=Phantom.fromjson(content.get_list_item(3)),
        )

    def __repr__(self):
        return "p4specast.CaseI(%r, %r, %r%s)" % (self.exp, self.cases, self.phantom, (", " + repr(self.region)) if self.region is not None else '')

def _combine_case_exp(exp, case):
    guard = case.guard
    #          | BoolG true -> exp.it
    if isinstance(guard, BoolG) and guard.value:
        exp_cond = exp
    #          | BoolG false -> Il.Ast.UnE (`NotOp, `BoolT, exp)
    elif isinstance(guard, BoolG) and not guard.value:
        exp_cond = UnE("NotOp", "BoolT", exp)
        exp_cond.typ = BoolT.INSTANCE
    #          | CmpG (cmpop, optyp, exp_r) ->
    #              Il.Ast.CmpE (cmpop, optyp, exp, exp_r)
    elif isinstance(guard, CmpG):
        exp_cond = CmpE(guard.op, guard.typ, exp, guard.exp)
        exp_cond.typ = BoolT.INSTANCE
    #          | SubG typ -> Il.Ast.SubE (exp, typ)
    elif isinstance(guard, SubG):
        exp_cond = SubE(exp, guard.typ)
        exp_cond.typ = BoolT.INSTANCE
    #          | MatchG pattern -> Il.Ast.MatchE (exp, pattern)
    elif isinstance(guard, MatchG):
        exp_cond = MatchE(exp, guard.pattern)
        exp_cond.typ = BoolT.INSTANCE
    #          | MemG exp_s -> Il.Ast.MemE (exp, exp_s)
    elif isinstance(guard, MemG):
        exp_cond = MemE(exp, guard.exp)
        exp_cond.typ = BoolT.INSTANCE
    else:
        #import pdb;pdb.set_trace()
        assert 0, 'missing case'
    return exp_cond

class OtherwiseI(Instr):
    def __init__(self, instr, region=None):
        self.instr = instr
        self.region = region

    def tostring(self, level=0, index=0):
        # | OtherwiseI instr ->
        #     Format.asprintf "%sOtherwise\n\n%s" order
        #       (string_of_instr ~level:(level + 1) ~index:1 instr)
        indent = "  " * level
        order = "%s%d. " % (indent, index)
        instr_str = self.instr.tostring(level + 1, 1)
        return "%sOtherwise\n\n%s" % (order, instr_str)

    @staticmethod
    def fromjson(content):
        return OtherwiseI(
            instr=Instr.fromjson(content.get_list_item(1))
        )

    def __repr__(self):
        return "p4specast.OtherwiseI(%r)" % (self.instr,)

class LetI(InstrWithIters):
    def __init__(self, var, value, iters, region=None):
        self.var = var
        self.value = value
        self.iters = iters
        self.region = region

    def tostring(self, level=0, index=0):
        # | LetI (exp_l, exp_r, iterexps) ->
        #     Format.asprintf "%s(Let %s be %s)%s" order (string_of_exp exp_l)
        #       (string_of_exp exp_r) (string_of_iterexps iterexps)
        indent = "  " * level
        order = "%s%d. " % (indent, index)
        iterexps_str = string_of_iterexps(self.iters)
        return "%s(Let %s be %s)%s" % (order, self.var.tostring(), self.value.tostring(), iterexps_str)

    @staticmethod
    def fromjson(content):
        return LetI(
            var=Exp.fromjson(content.get_list_item(1)),
            value=Exp.fromjson(content.get_list_item(2)),
            iters=[IterExp.fromjson(ite) for ite in content.get_list_item(3).value_array()]
        )

    def __repr__(self):
        return "p4specast.LetI(%r, %r, %r%s)" % (self.var, self.value, self.iters, (", " + repr(self.region)) if self.region is not None else '')

class RuleI(InstrWithIters):
    def __init__(self, id, notexp, iters, region=None):
        self.id = id
        self.notexp = notexp
        self.iters = iters
        self.region = region

    def tostring(self, level=0, index=0):
        # | RuleI (id_rel, notexp, iterexps) ->
        #     Format.asprintf "%s(%s: %s)%s" order (string_of_relid id_rel)
        #       (string_of_notexp notexp) (string_of_iterexps iterexps)
        indent = "  " * level
        order = "%s%d. " % (indent, index)
        iterexps_str = string_of_iterexps(self.iters)
        return "%s(%s: %s)%s" % (order, self.id.value, self.notexp.tostring(), iterexps_str)

    @staticmethod
    def fromjson(content):
        return RuleI(
            id=Id.fromjson(content.get_list_item(1)),
            notexp=NotExp.fromjson(content.get_list_item(2)),
            iters=[IterExp.fromjson(ite) for ite in content.get_list_item(3).value_array()]
        )

    def __repr__(self):
        return "p4specast.RuleI(%r, %r, %r%s)" % (self.id, self.notexp, self.iters, (", " + repr(self.region)) if self.region is not None else '')

class ResultI(Instr):
    def __init__(self, exps, region=None):
        self.exps = exps
        self.region = region

    def tostring(self, level=0, index=0):
        # | ResultI [] -> Format.asprintf "%sThe relation holds" order
        # | ResultI exps -> Format.asprintf "%sResult in %s" order (string_of_exps ", " exps)
        indent = "  " * level
        order = "%s%d. " % (indent, index)
        if not self.exps:
            return "%sThe relation holds" % order
        else:
            exps_str = ", ".join([e.tostring() for e in self.exps])
            return "%sResult in %s" % (order, exps_str)

    @staticmethod
    def fromjson(content):
        return ResultI(
            exps=[Exp.fromjson(elt) for elt in content.get_list_item(1).value_array()]
        )

    def __repr__(self):
        return "p4specast.ResultI(%r%s)" % (self.exps, (", " + repr(self.region)) if self.region is not None else '')

class ReturnI(Instr):
    def __init__(self, exp, region=None):
        self.exp = exp
        self.region = region

    def tostring(self, level=0, index=0):
        # | ReturnI exp -> Format.asprintf "%sReturn %s" order (string_of_exp exp)
        indent = "  " * level
        order = "%s%d. " % (indent, index)
        return "%sReturn %s" % (order, self.exp.tostring())

    @staticmethod
    def fromjson(content):
        return ReturnI(
            exp=Exp.fromjson(content.get_list_item(1))
        )

    def __repr__(self):
        return "p4specast.ReturnI(%r%s)" % (self.exp, (", " + repr(self.region)) if self.region is not None else '')


#and holdcase =
#  | BothH of instr list * instr list
#  | HoldH of instr list * phantom option
#  | NotHoldH of instr list * phantom option

#and string_of_holdcase ?(level = 0) holdcase =
#  let indent = String.make (level * 2) ' ' in
#  match holdcase with

class HoldCase(AstBase):
    # abstract base
    @staticmethod
    def fromjson(value):
        what = value.get_list_item(0).value_string()
        if what == 'BothH':
            return BothH.fromjson(value)
        elif what == 'HoldH':
            return HoldH.fromjson(value)
        elif what == 'NotHoldH':
            return NotHoldH.fromjson(value)
        else:
            raise P4UnknownTypeError("Unknown HoldCase: %s" % what)

    def tostring(self, level=0):
        raise P4NotImplementedError('abstract base class')


class BothH(HoldCase):
    def __init__(self, hold_instrs, nothold_instrs):
        self.hold_instrs = hold_instrs
        self.nothold_instrs = nothold_instrs

    @staticmethod
    def fromjson(content):
        return BothH(
            hold_instrs=[Instr.fromjson(instr) for instr in content.get_list_item(1).value_array()],
            nothold_instrs=[Instr.fromjson(instr) for instr in content.get_list_item(2).value_array()]
        )

    def tostring(self, level=0):
        #  let indent = String.make (level * 2) ' ' in
        #  | BothH (instrs_hold, instrs_nothold) ->
        #      Format.asprintf "%sHolds:\n\n%s\n\n%sDoes not hold:\n\n%s" indent
        #        (string_of_instrs ~level:(level + 1) instrs_hold)
        #        indent
        #        (string_of_instrs ~level:(level + 1) instrs_nothold)
        indent = "  " * (level * 2)
        hold_str = string_of_instrs(self.hold_instrs, level + 1)
        nothold_str = string_of_instrs(self.nothold_instrs, level + 1)
        return "%sHolds:\n\n%s\n\n%sDoes not hold:\n\n%s" % (indent, hold_str, indent, nothold_str)

    def __repr__(self):
        return "p4specast.BothH(%r, %r)" % (self.hold_instrs, self.nothold_instrs)


class HoldH(HoldCase):
    def __init__(self, hold_instrs, phantom):
        self.hold_instrs = hold_instrs
        self.phantom = phantom

    @staticmethod
    def fromjson(content):
        return HoldH(
            hold_instrs=[Instr.fromjson(instr) for instr in content.get_list_item(1).value_array()],
            phantom=Phantom.fromjson(content.get_list_item(2)),
        )

    def tostring(self, level=0):
        #  let indent = String.make (level * 2) ' ' in
        #  | HoldH (instrs_hold, None) ->
        #      Format.asprintf "%sHolds:\n\n%s" indent
        #        (string_of_instrs ~level:(level + 1) instrs_hold)
        #  | HoldH (instrs_hold, Some phantom) ->
        #      Format.asprintf "%sHolds:\n\n%s\n\n%sElse %s" indent
        #        (string_of_instrs ~level:(level + 1) instrs_hold)
        #        indent
        #        (string_of_phantom phantom)
        indent = "  " * (level * 2)
        hold_str = string_of_instrs(self.hold_instrs, level + 1)
        if self.phantom.is_null:  # None case
            return "%sHolds:\n\n%s" % (indent, hold_str)
        else:  # Some phantom case
            phantom_str = self.phantom.tostring()
            return "%sHolds:\n\n%s\n\n%sElse %s" % (indent, hold_str, indent, phantom_str)

    def __repr__(self):
        return "p4specast.HoldH(%r, %r)" % (self.hold_instrs, self.phantom)

class NotHoldH(HoldCase):
    def __init__(self, nothold_instrs, phantom):
        self.nothold_instrs = nothold_instrs
        self.phantom = phantom

    @staticmethod
    def fromjson(content):
        return NotHoldH(
            nothold_instrs=[Instr.fromjson(instr) for instr in content.get_list_item(1).value_array()],
            phantom=Phantom.fromjson(content.get_list_item(2)),
        )

    def tostring(self, level=0):
        #  let indent = String.make (level * 2) ' ' in
        #  | NotHoldH (instrs_nothold, None) ->
        #      Format.asprintf "%sDoes not hold:\n\n%s" indent
        #        (string_of_instrs ~level:(level + 1) instrs_nothold)
        #  | NotHoldH (instrs_nothold, Some phantom) ->
        #      Format.asprintf "%sDoes not hold:\n\n%s\n\n%sElse %s" indent
        #        (string_of_instrs ~level:(level + 1) instrs_nothold)
        #        indent
        #        (string_of_phantom phantom)
        indent = "  " * (level * 2)
        nothold_str = string_of_instrs(self.nothold_instrs, level + 1)
        if self.phantom.is_null:  # None case
            return "%sDoes not hold:\n\n%s" % (indent, nothold_str)
        else:  # Some phantom case
            phantom_str = self.phantom.tostring()
            return "%sDoes not hold:\n\n%s\n\n%sElse %s" % (indent, nothold_str, indent, phantom_str)


    def __repr__(self):
        return "p4specast.NotHoldH(%r, %r)" % (self.nothold_instrs, self.phantom)


# cases
# and case = guard * instr list

# and guard =
#   | BoolG of bool
#   | CmpG of cmpop * optyp * exp
#   | SubG of typ
#   | MatchG of pattern
#   | MemG of exp

class Case(AstBase):
    def __init__(self, guard, instrs):
        self.guard = guard
        self.instrs = instrs

    def tostring(self, level=0, index=0):
        # and string_of_case ?(level = 0) ?(index = 0) case =
        #   let indent = String.make (level * 2) ' ' in
        #   let order = Format.asprintf "%s%d. " indent index in
        #   let guard, instrs = case in
        #   Format.asprintf "%sCase %s\n\n%s" order (string_of_guard guard)
        #     (string_of_instrs ~level:(level + 1) instrs)
        indent = "  " * level
        order = "%s%d. " % (indent, index)
        instrs_str = string_of_instrs(self.instrs, level + 1)
        return "%sCase %s\n\n%s" % (order, self.guard.tostring(), instrs_str)

    @staticmethod
    def fromjson(content):
        return Case(
            guard=Guard.fromjson(content.get_list_item(0)),
            instrs=[Instr.fromjson(instr) for instr in content.get_list_item(1).value_array()]
        )

    def __repr__(self):
        return "p4specast.Case(%r, %r)" % (self.guard, self.instrs)


class Guard(AstBase):
    def tostring(self):
        assert 0  # abstract method

    @staticmethod
    def fromjson(content):
        kind = content.get_list_item(0).value_string()
        if kind == 'BoolG':
            return BoolG.fromjson(content)
        elif kind == 'CmpG':
            return CmpG.fromjson(content)
        elif kind == 'SubG':
            return SubG.fromjson(content)
        elif kind == 'MatchG':
            return MatchG.fromjson(content)
        elif kind == 'MemG':
            return MemG.fromjson(content)
        else:
            raise P4UnknownTypeError("Unknown Guard: %s" % kind)

class BoolG(Guard):
    def __init__(self, value):
        self.value = value # typ: bool

    def tostring(self):
        # | BoolG b -> string_of_bool b
        return "true" if self.value else "false"

    @staticmethod
    def fromjson(content):
        return BoolG(
            value=content.get_list_item(1).value_bool()
        )

    def __repr__(self):
        return "p4specast.BoolG(%r)" % (self.value,)

class CmpG(Guard):
    def __init__(self, op, typ, exp):
        self.op = op # typ: cmpop
        self.typ = typ # typ: optyp
        self.exp = exp # typ: exp

    def tostring(self):
        # | CmpG (cmpop, _, exp) -> "(% " ^ string_of_cmpop cmpop ^ " " ^ string_of_exp exp ^ ")"
        cmpop_map = {
            "EqOp": "=",
            "NeOp": "=/=",
            "LtOp": "<",
            "GtOp": ">",
            "LeOp": "<=",
            "GeOp": ">="
        }
        cmpop_str = cmpop_map.get(self.op, "?%s?" % self.op)
        return "(%% %s %s)" % (cmpop_str, self.exp.tostring())

    @staticmethod
    def fromjson(content):
        return CmpG(
            op=content.get_list_item(1).get_list_item(0).value_string(),
            typ=content.get_list_item(2).get_list_item(0).value_string(),
            exp=Exp.fromjson(content.get_list_item(3))
        )

    def __repr__(self):
        return "p4specast.CmpG(%r, %r, %r)" % (self.op, self.typ, self.exp)

class SubG(Guard):
    def __init__(self, typ):
        self.typ = typ # typ: Type

    def tostring(self):
        # | SubG typ -> "(% has type " ^ string_of_typ typ ^ ")"
        return "(%% has type %s)" % self.typ.tostring()

    @staticmethod
    def fromjson(content):
        return SubG(
            typ=Type.fromjson(content.get_list_item(1))
        )

    def __repr__(self):
        return "p4specast.SubG(%r)" % (self.typ,)

class MatchG(Guard):
    def __init__(self, pattern):
        self.pattern = pattern # typ: Pattern

    def tostring(self):
        # | MatchG patten -> "(% matches pattern " ^ string_of_pattern patten ^ ")"
        return "(%% matches pattern %s)" % self.pattern.tostring()

    @staticmethod
    def fromjson(content):
        return MatchG(
            pattern=Pattern.fromjson(content.get_list_item(1))
        )

    def __repr__(self):
        return "p4specast.MatchG(%r)" % (self.pattern,)

class MemG(Guard):
    def __init__(self, exp):
        self.exp = exp # typ: Exp

    def tostring(self):
        # | MemG exp -> "(% is in " ^ string_of_exp exp ^ ")"
        return "(%% is in %s)" % self.exp.tostring()

    @staticmethod
    def fromjson(content):
        return MemG(
            exp=Exp.fromjson(content.get_list_item(1))
        )

    def __repr__(self):
        return "p4specast.MemG(%r)" % (self.exp,)

# and pattern =
#   | casep of mixop
#   | listp of [ `cons | `fixed of int | `nil ]
#   | optp of [ `some | `none ]

class Pattern(AstBase):
    def tostring(self):
        assert 0  # abstract method

    @staticmethod
    def fromjson(content):
        kind = content.get_list_item(0).value_string()
        if kind == 'CaseP':
            return CaseP.fromjson(content)
        elif kind == 'ListP':
            return ListP.fromjson(content)
        elif kind == 'OptP':
            return OptP.fromjson(content)
        else:
            raise P4UnknownTypeError("Unknown Pattern: %s" % kind)

class CaseP(Pattern):
    def __init__(self, mixop):
        self.mixop = mixop # typ: mixop

    def tostring(self):
        # | CaseP mixop -> string_of_mixop mixop
        return self.mixop.tostring()

    @staticmethod
    def fromjson(content):
        return CaseP(
            mixop=MixOp.fromjson(content.get_list_item(1))
        )

    def __repr__(self):
        return "p4specast.CaseP(%r)" % (self.mixop,)

class ListP(Pattern):
    def __init__(self, element):
        self.element = element # typ: ListPElem

    def tostring(self):
        # | ListP `Cons -> "_ :: _"
        # | ListP (`Fixed len) -> Format.asprintf "[ _/%d ]" len
        # | ListP `Nil -> "[]"
        if isinstance(self.element, Cons):
            return "_ :: _"
        elif isinstance(self.element, Fixed):
            return "[ _/%d ]" % self.element.value
        elif isinstance(self.element, Nil):
            return "[]"
        else:
            assert 0, "Unknown ListP element: %s" % self.element

    @staticmethod
    def fromjson(content):
        return ListP(
            element=ListPElem.fromjson(content.get_list_item(1))
        )

    def __repr__(self):
        return "p4specast.ListP(%r)" % (self.element,)

class OptP(Pattern):
    def __init__(self, kind):
        self.kind = kind # "Some" | "None"

    def tostring(self):
        # | OptP `Some -> "(_)"
        # | OptP `None -> "()"
        if self.kind == "Some":
            return "(_)"
        elif self.kind == "None":
            return "()"
        else:
            assert 0, "Unknown OptP kind: %s" % self.kind

    @staticmethod
    def fromjson(content):
        return OptP(
            kind=content.get_list_item(1).get_list_item(0).value_string()
        )

    def __repr__(self):
        return "p4specast.OptP(%r)" % (self.kind,)

# [ `cons | `fixed of int | `nil ]

class ListPElem(AstBase):
    @staticmethod
    def fromjson(content):
        kind = content.get_list_item(0).value_string()
        if kind == 'Cons':
            return Cons()
        elif kind == 'Fixed':
            return Fixed(content.get_list_item(1).value_int())
        elif kind == 'Nil':
            return Nil()
        else:
            raise P4UnknownTypeError("Unknown ListPElem: %s" % kind)

class Cons(ListPElem):
    def __repr__(self):
        return "p4specast.Cons()"

class Fixed(ListPElem):
    def __init__(self, value):
        self.value = value # typ: int

    def __repr__(self):
        return "p4specast.Fixed(%r)" % (self.value,)

class Nil(ListPElem):
    def __repr__(self):
        return "p4specast.Nil()"



# and path = (path', typ') note_phrase
# and path' =
#   | RootP                        (*  *)
#   | IdxP of path * exp           (* path `[` exp `]` *)
#   | SliceP of path * exp * exp   (* path `[` exp `:` exp `]` *)
#   | DotP of path * atom          (* path `.` atom *)

class Path(AstBase):
    # has a region and a type (in the 'note' json field)

    def tostring(self):
        assert 0  # abstract method

    @staticmethod
    def fromjson(value):
        region = Region.fromjson(value.get_dict_value('at'))
        content = value.get_dict_value('it')
        typ = Type.fromjson(value.get_dict_value('note'))
        kind = content.get_list_item(0).value_string()
        if kind == 'RootP':
            ast = RootP()
        elif kind == 'IdxP':
            ast = IdxP.fromjson(content)
        elif kind == 'SliceP':
            ast = SliceP.fromjson(content)
        elif kind == 'DotP':
            ast = DotP.fromjson(content)
        else:
            raise P4UnknownTypeError("Unknown Path: %s" % kind)
        ast.region = region
        ast.typ = typ
        return ast

class RootP(Path):
    def tostring(self):
        # | RootP -> ""
        return ""

    @staticmethod
    def fromjson(content):
        return RootP()

    def __repr__(self):
        return "p4specast.RootP()"

class IdxP(Path):
    def __init__(self, path, exp):
        self.path = path
        self.exp = exp

    def tostring(self):
        # | IdxP (path, exp) -> string_of_path path ^ "[" ^ string_of_exp exp ^ "]"
        return "%s[%s]" % (self.path.tostring(), self.exp.tostring())

    @staticmethod
    def fromjson(content):
        return IdxP(
            path=Path.fromjson(content.get_list_item(1)),
            exp=Exp.fromjson(content.get_list_item(2))
        )

    def __repr__(self):
        return "p4specast.IdxP(%r, %r)" % (self.path, self.exp)

class SliceP(Path):
    def __init__(self, path, start, end):
        self.path = path
        self.start = start
        self.end = end

    def tostring(self):
        # | SliceP (path, exp_l, exp_h) ->
        #     string_of_path path ^ "[" ^ string_of_exp exp_l ^ " : "
        #     ^ string_of_exp exp_h ^ "]"
        return "%s[%s : %s]" % (self.path.tostring(), self.start.tostring(), self.end.tostring())

    @staticmethod
    def fromjson(content):
        return SliceP(
            path=Path.fromjson(content.get_list_item(1)),
            start=Exp.fromjson(content.get_list_item(2)),
            end=Exp.fromjson(content.get_list_item(3))
        )

    def __repr__(self):
        return "p4specast.SliceP(%r, %r, %r)" % (self.path, self.start, self.end)

class DotP(Path):
    def __init__(self, path, atom):
        self.path = path
        self.atom = atom

    def tostring(self):
        # | DotP ({ it = RootP; _ }, atom) -> string_of_atom atom
        # | DotP (path, atom) -> string_of_path path ^ "." ^ string_of_atom atom
        if isinstance(self.path, RootP):
            return self.atom.value
        else:
            return "%s.%s" % (self.path.tostring(), self.atom.value)

    @staticmethod
    def fromjson(content):
        return DotP(
            path=Path.fromjson(content.get_list_item(1)),
            atom=AtomT.fromjson(content.get_list_item(2))
        )

    def __repr__(self):
        return "p4specast.DotP(%r, %r)" % (self.path, self.atom)

# and pid = int
# and phantom = pid * pathcond list

class Phantom(AstBase):
    def __init__(self, pid, pathconds):
        self.pid = pid # type: int
        self.pathconds = pathconds # type: list[PathCond]

    def tostring(self):
        # and string_of_pid pid = Format.asprintf "Phantom#%d" pid

        # and string_of_phantom phantom =
        #   let pid, _ = phantom in
        #   string_of_pid pid
        return "Phantom#%d" % self.pid

    def tostring_of_pathconds(self):
        #  and string_of_pathconds pathconds =
        #   List.map string_of_pathcond pathconds |> String.concat " /\\ "
       return " /\\ ".join([pc.tostring() for pc in self.pathconds])

    @staticmethod
    def fromjson(content):
        if content.is_null:
            return None
        return Phantom(
            pid=content.get_list_item(0).value_int(),
            pathconds=[PathCond.fromjson(pc) for pc in content.get_list_item(1).value_array()]
        )

    def __repr__(self):
        return "p4specast.Phantom(%r, %r)" % (self.pid, self.pathconds)



# and pathcond =
#   | ForallC of pathcond * iterexp list
#   | ExistsC of pathcond * iterexp list
#   | PlainC of exp
#   | HoldC of id * notexp
#   | NotHoldC of id * notexp

# and string_of_pathcond pathcond =
#   match pathcond with
#   | ForallC (pathcond, iterexps) ->
#       Format.asprintf "(forall %s)%s"
#         (string_of_pathcond pathcond)
#         (string_of_iterexps iterexps)
#   | ExistsC (pathcond, iterexps) ->
#       Format.asprintf "(exists %s)%s"
#         (string_of_pathcond pathcond)
#         (string_of_iterexps iterexps)
#   | PlainC exp -> "(" ^ string_of_exp exp ^ ")"
#   | HoldC (relid, notexp) ->
#       Format.asprintf "(%s: %s holds)" (string_of_relid relid)
#         (string_of_notexp notexp)
#   | NotHoldC (relid, notexp) ->
#       Format.asprintf "(%s: %s does not hold)" (string_of_relid relid)
#         (string_of_notexp notexp)


class PathCond(AstBase):
    @staticmethod
    def fromjson(value):
        kind = value.get_list_item(0).value_string()
        if kind == 'ForallC':
            return ForallC.fromjson(value)
        elif kind == 'ExistsC':
            return ExistsC.fromjson(value)
        elif kind == 'PlainC':
            return PlainC.fromjson(value)
        elif kind == 'HoldC':
            return HoldC.fromjson(value)
        elif kind == 'NotHoldC':
            return NotHoldC.fromjson(value)
        else:
            raise P4UnknownTypeError("Unknown PathCond: %s" % kind)

    def tostring(self):
        assert 0  # abstract method


class ForallC(PathCond):
    def __init__(self, pathcond, iters):
        self.pathcond = pathcond # type: PathCond
        self.iters = iters # type: list[IterExp]

    def tostring(self):
        # | ForallC (pathcond, iterexps) ->
        #     Format.asprintf "(forall %s)%s"
        #       (string_of_pathcond pathcond)
        #       (string_of_iterexps iterexps)
        return "(forall %s)%s" % (
            self.pathcond.tostring(),
            string_of_iterexps(self.iters)
        )

    @staticmethod
    def fromjson(content):
        return ForallC(
            pathcond=PathCond.fromjson(content.get_list_item(1)),
            iters=[IterExp.fromjson(ite) for ite in content.get_list_item(2).value_array()]
        )

    def __repr__(self):
        return "p4specast.ForallC(%r, %r)" % (self.pathcond, self.iters)


class ExistsC(PathCond):
    def __init__(self, pathcond, iters):
        self.pathcond = pathcond # type: PathCond
        self.iters = iters # type: list[IterExp]

    def tostring(self):
        # | ExistsC (pathcond, iterexps) ->
        #     Format.asprintf "(exists %s)%s"
        #       (string_of_pathcond pathcond)
        #       (string_of_iterexps iterexps)
        return "(exists %s)%s" % (
            self.pathcond.tostring(),
            string_of_iterexps(self.iters)
        )

    @staticmethod
    def fromjson(content):
        return ExistsC(
            pathcond=PathCond.fromjson(content.get_list_item(1)),
            iters=[IterExp.fromjson(ite) for ite in content.get_list_item(2).value_array()]
        )

    def __repr__(self):
        return "p4specast.ExistsC(%r, %r)" % (self.pathcond, self.iters)


class PlainC(PathCond):
    def __init__(self, exp):
        self.exp = exp # type: Exp

    def tostring(self):
        # | PlainC exp -> "(" ^ string_of_exp exp ^ ")"
        return "(%s)" % self.exp.tostring()

    @staticmethod
    def fromjson(content):
        return PlainC(
            exp=Exp.fromjson(content.get_list_item(1))
        )

    def __repr__(self):
        return "p4specast.PlainC(%r)" % (self.exp,)


class HoldC(PathCond):
    def __init__(self, id, notexp):
        self.id = id # type: Id
        self.notexp = notexp # type: NotExp

    def tostring(self):
        # | HoldC (relid, notexp) ->
        #     Format.asprintf "(%s: %s holds)" (string_of_relid relid)
        #       (string_of_notexp notexp)
        return "(%s: %s holds)" % (
            self.id.value,
            self.notexp.tostring()
        )

    @staticmethod
    def fromjson(content):
        return HoldC(
            id=Id.fromjson(content.get_list_item(1)),
            notexp=NotExp.fromjson(content.get_list_item(2))
        )

    def __repr__(self):
        return "p4specast.HoldC(%r, %r)" % (self.id, self.notexp)

class NotHoldC(PathCond):
    def __init__(self, id, notexp):
        self.id = id # type: Id
        self.notexp = notexp # type: NotExp

    def tostring(self):
        # | NotHoldC (relid, notexp) ->
        #     Format.asprintf "(%s: %s does not hold)" (string_of_relid relid)
        #       (string_of_notexp notexp)
        return "(%s: %s does not hold)" % (
            self.id.value,
            self.notexp.tostring()
        )

    @staticmethod
    def fromjson(content):
        return NotHoldC(
            id=Id.fromjson(content.get_list_item(1)),
            notexp=NotExp.fromjson(content.get_list_item(2))
        )

    def __repr__(self):
        return "p4specast.NotHoldC(%r, %r)" % (self.id, self.notexp)


# type Mixop.t = Atom.t phrase list list

class MixOp(AstBase):
    def __init__(self, phrases):
        self.phrases = phrases # type: list[list[AtomT]]

    def compare(self, other):
        # type: (MixOp, MixOp) -> int
        """ Compare two MixOp objects lexicographically by their phrases
        Each phrase is a list of AtomT
        Returns -1 if self < other, 0 if equal, 1 if self > other """

        def phrase_compare(phrase_a, phrase_b):
            # Compare two lists of AtomT
            len_a = len(phrase_a)
            len_b = len(phrase_b)
            for i in range(min(len_a, len_b)):
                cmp = phrase_a[i].compare(phrase_b[i])
                if cmp != 0:
                    return cmp
            if len_a < len_b:
                return -1
            elif len_a > len_b:
                return 1
            else:
                return 0

        phrases_a = self.phrases
        phrases_b = other.phrases
        len_a = len(phrases_a)
        len_b = len(phrases_b)
        for i in range(min(len_a, len_b)):
            cmp = phrase_compare(phrases_a[i], phrases_b[i])
            if cmp != 0:
                return cmp
        if len_a < len_b:
            return -1
        elif len_a > len_b:
            return 1
        else:
            return 0

    @staticmethod
    def fromjson(content):
        return MixOp(
            phrases=[[AtomT.fromjson(phrase) for phrase in group.value_array()] for group in content.value_array()]
        )

    def tojson(self):
        from rpyp4sp import rpyjson
        phrases_json = []
        for phrase_group in self.phrases:
            group_json = [atom.tojson() for atom in phrase_group]
            phrases_json.append(rpyjson.JsonArray(group_json))
        return rpyjson.JsonArray(phrases_json)

    def __repr__(self):
        return "p4specast.MixOp(%r)" % (self.phrases,)

    def tostring(self):
        mixop = self.phrases
        smixop = "%".join(
            ["".join([atom.value for atom in atoms]) for atoms in mixop]
        )
        return "`" + smixop + "`"

    def __str__(self):
        return self.tostring()


class AtomT(AstBase):
    def __init__(self, value, region=NO_REGION):
        self.value = value # type: str
        self.region = region # type: Region

    def tostring(self):
        return self.value

    def __repr__(self):
        repr_region = repr(self.region)
        if repr_region == "p4specast.NO_REGION":
            return "p4specast.AtomT(%r)" % (self.value,)
        if self.region.is_line_span():
            return "p4specast.AtomT.line_span(%r, %r, %r, %r, %r)" % (
                self.value,
                self.region.left.file,
                self.region.left.line,
                self.region.left.column,
                self.region.right.column,
            )
        return "p4specast.AtomT(%r, %s)" % (self.value, repr_region)

    def compare(self, other):
        # type: (AtomT, AtomT) -> int
        # TODO: is this right?
        if self.value == other.value:
            return 0
        if self.value < other.value:
            return -1
        return 1


    @staticmethod
    def line_span(value, file, line, col_start, col_end):
        return AtomT(
            value=value,
            region=Region.line_span(file, line, col_start, col_end)
        )

    @staticmethod
    def fromjson(value):
        region = Region.fromjson(value.get_dict_value('at'))
        content = value.get_dict_value('it')
        kind = content.get_list_item(0).value_string()
        if kind == 'Atom':
            return AtomT(
                value=content.get_list_item(1).value_string(),
                region=region
            )
        else:
            return AtomT(
                value=atom_type_to_value(kind),
                region=region
            )

    def tojson(self):
        from rpyp4sp import rpyjson
        # Find the atom type for this value, or use 'Atom' as default
        atom_type = None
        for type_name, type_value in atom_type_map.items():
            if type_value == self.value:
                atom_type = type_name
                break

        if atom_type is not None:
            content = rpyjson.JsonArray([rpyjson.JsonString(atom_type)])
        else:
            content = rpyjson.JsonArray([rpyjson.JsonString('Atom'), rpyjson.JsonString(self.value)])

        atom_map = rpyjson.ROOT_MAP.get_next("it").get_next("note").get_next("at")
        return rpyjson.JsonObject3(atom_map, content, rpyjson.json_null, self.region.tojson())

def atom_type_to_value(kind):
    return atom_type_map[kind]

atom_type_map = {
    'Infinity': 'infinity',
    'Bot': '_|_',
    'Top': '^|^',
    'Dot': '.',
    'Dot2': '..',
    'Dot3': '...',
    'Semicolon': ';',
    'Backslash': '\\',
    'Mem': '<-',
    'Arrow': '->',
    'Arrow2': '=>',
    'ArrowSub': '->_',
    'Arrow2Sub': '=>_',
    'Colon': ':',
    'Sub': '<:',
    'Sup': ':>',
    'Assign': ':=',
    'Equal': '=',
    'NotEqual': '=/=',
    'Less': '<',
    'Greater': '>',
    'LessEqual': '<=',
    'GreaterEqual': '>=',
    'Equiv': '==',
    'Approx': '~~',
    'SqArrow': '~>',
    'SqArrowStar': '~>*',
    'Prec': '<<',
    'Succ': '>>',
    'Tilesturn': '-|',
    'Turnstile': '|-',
    'Quest': '?',
    'Plus': '+',
    'Star': '*',
    'Comma': ',',
    'Cat': '++',
    'Bar': '|',
    'BigAnd': '(/\\)',
    'BigOr': '(\\/)',
    'BigAdd': '(+)',
    'BigMul': '(*)',
    'BigCat': '(++)',
    'LParen': '(',
    'LBrack': '[',
    'LBrace': '{',
    'RParen': ')',
    'RBrack': ']',
    'RBrace': '}',
}
