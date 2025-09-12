from rpython.tool.pairtype import extendabletype
from rpyp4sp import integers

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
        label = [type(self).__name__]
        for key, value in self.__dict__.items():
            if key == 'phantom':
                continue
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
        raise NotImplementedError('abstract base')


def define_enum(basename, *names):
    class Base(AstBase):
        @staticmethod
        def fromjson(value):
            content, = value.value_array()
            content = content.value_string()
            for name, cls in unrolling_tups:
                if name == content:
                    return cls()
            assert 0

        def __repr__(self):
            return "p4specast." + type(self).__name__ + "()"
    Base.__name__ = basename
    subs = []
    for name in names:
        class Sub(Base):
            pass
        Sub.__name__ = name
        subs.append(Sub)
    unrolling_tups = [(name, cls) for name, cls in zip(names, subs)]
    return [Base] + subs


# type pos = { file : string; line : int; column : int } [@@deriving yojson]


class Position(AstBase):
    def __init__(self, file, line, column):
        self.file = file # type: str
        self.line = line # type: int
        self.column = column # type: int

    @staticmethod
    def fromjson(value):
        return Position(value['file'].value_string(), value['line'].value_int(), value['column'].value_int())

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
        return Region(Position.fromjson(value['left']), Position.fromjson(value['right']))

    @staticmethod
    def line_span(file, line, column_start, column_end):
        return Region(Position(file, line, column_start), Position(file, line, column_end))

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
        region = Region.fromjson(value['at'])
        return Id(
            value["it"].value_string(),
            region
        )

    def __repr__(self):
        return "p4specast.Id(%r, %s)" % (self.value, self.region)

class TParam(AstBase):
    def __init__(self, value, region):
        self.value = value # type: str
        self.region = region # type: Region

    @staticmethod
    def fromjson(value):
        return TParam(
            value['it'].value_string(),
            Region.fromjson(value['at'])
        )

    def __repr__(self):
        return "p4specast.TParam(value=%s, region=%s)" % (self.value, self.region)

# and targ = targ' phrase [@@deriving yojson]
# and targ' = typ' [@@deriving yojson]

class TArg(AstBase):
    def __init__(self, typ, region):
        self.typ = typ # type: Type
        self.region = region # type: Region

    @staticmethod
    def fromjson(value):
        return TArg(
            Type.fromjson(value['it']),
            Region.fromjson(value['at'])
        )

    def __repr__(self):
        return "p4specast.TArg(typ=%s, region=%s)" % (self.typ, self.region)


# type iter =
#   | Opt       (* `?` *)
#   | List      (* `*` *)

Iter, Opt, List = define_enum('Iter', 'Opt', 'List')

# type var = id * typ * iter list

class Var(AstBase):
    def __init__(self, id, typ, iter):
        self.id = id
        self.typ = typ
        self.iter = iter

    def __repr__(self):
        return "p4specast.Var(id=%s, typ=%s, iter=%s)" % (self.id, self.typ, self.iter)

    @staticmethod
    def fromjson(content):
        return Var(
            id=Id.fromjson(content[0]),
            typ=Type.fromjson(content[1]),
            iter=[Iter.fromjson(i) for i in content[2].value_array()]
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
        assert value['note'].is_null
        region = Region.fromjson(value['at'])
        content = value['it']
        what = content[0].value_string()
        if what == 'DecD':
            ast = DecD.fromjson(content)
        elif what == 'TypD':
            ast = TypD.fromjson(content)
        elif what == 'RelD':
            ast = RelD.fromjson(content)
        else:
            raise ValueError("Unknown Def type: %s" % what)
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
        _, id, tparams_value, deftype_value = value
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
        _, id, mixop_and_ints, exps_value, instrs_value = value
        mixop = MixOp.fromjson(mixop_and_ints[0])
        inputs = [i.value_int() for i in mixop_and_ints[1].value_array()]
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
        _, id, tparams_value, args_value, instrs_value = value
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
    @staticmethod
    def fromjson(value):
        assert value['note'].is_null
        region = Region.fromjson(value['at'])
        content = value['it']
        what = content[0].value_string()
        if what == 'ExpA':
            return ExpA.fromjson(content)
        elif what == 'DefA':
            return DefA.fromjson(content)
        else:
            raise ValueError("Unknown Arg type: %s" % what)

class ExpA(Arg):
    def __init__(self, exp):
        self.exp = exp # typ: Exp

    def __repr__(self):
        return "p4specast.ExpA(%r)" % (self.exp,)

    @staticmethod
    def fromjson(value):
        _, exp_value = value
        return ExpA(
            exp=Exp.fromjson(exp_value)
        )

class DefA(Arg):
    def __init__(self, id):
        self.id = id # typ: Id

    def __repr__(self):
        return "p4specast.DefA(%r)" % (self.id,)

    @staticmethod
    def fromjson(value):
        _, id_value = value
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
#   | HoldE of id * notexp                  (* id `:` notexp `holds` *)
#   | IterE of exp * iterexp                (* exp iterexp *)


class Exp(AstBase):
    # has .typ (with is in 'note' field of json) and a region

    @staticmethod
    def fromjson(value):
        typ = Type.fromjson(value['note'])
        region = Region.fromjson(value['at'])
        content = value['it']
        what = content[0].value_string()
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
        elif what == 'HoldE':
            ast = HoldE.fromjson(content)
        elif what == 'IterE':
            ast = IterE.fromjson(content)
        else:
            raise ValueError("Unknown Exp type: %s" % what)
        ast.typ = typ
        ast.region = region
        return ast


class BoolE(Exp):
    def __init__(self, value):
        assert isinstance(value, bool)
        self.value = value # type: bool

    @staticmethod
    def fromjson(content):
        return BoolE(
            value=content[1].value_bool()
        )

    def __repr__(self):
        return "p4specast.BoolE(%r)" % (self.value,)


class NumE(Exp):
    def __init__(self, value, what, typ=None):
        self.value = value # type: integers.Integer
        self.what = what # type: str
        self.typ = typ # type: Type

    @staticmethod
    def fromjson(content):
        what = content[1][0].value_string()
        return NumE.fromstr(content[1][1].value_string(), what)

    @staticmethod
    def fromstr(valuestr, what, typ=None):
        return NumE(integers.Integer.fromstr(valuestr),
                    what, typ)

    def __repr__(self):
        return "p4specast.NumE.fromstr(%r, %r)" % (self.value.str(), self.what)


class TextE(Exp):
    def __init__(self, value):
        self.value = value # typ: str

    @staticmethod
    def fromjson(content):
        return TextE(
            value=content[1].value_string()
        )

    def __repr__(self):
        return "p4specast.TextE(%r)" % (self.value,)

class VarE(Exp):
    def __init__(self, id):
        self.id = id # typ: id

    @staticmethod
    def fromjson(content):
        return VarE(
            id=Id.fromjson(content[1])
        )

    def __repr__(self):
        return "p4specast.VarE(%r)" % (self.id,)

class UnE(Exp):
    #   | UnE of unop * optyp * exp             (* unop exp *)
    def __init__(self, op, optyp, exp):
        self.op = op # typ: unop
        self.optyp = optyp # typ: optyp
        self.exp = exp # typ: Exp

    def __repr__(self):
        return "p4specast.UnE(%r, %r, %r)" % (self.op, self.optyp, self.exp)

    @staticmethod
    def fromjson(content):
        return UnE(
            op=content[1][0].value_string(),
            optyp=content[2][0].value_string(),
            exp=Exp.fromjson(content[3])
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

    @staticmethod
    def fromjson(content):
        return BinE(
            binop=content[1][0].value_string(),
            optyp=content[2][0].value_string(),
            left=Exp.fromjson(content[3]),
            right=Exp.fromjson(content[4])
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

    @staticmethod
    def fromjson(content):
        return CmpE(
            cmpop=content[1][0].value_string(),
            optyp=content[2][0].value_string(),
            left=Exp.fromjson(content[3]),
            right=Exp.fromjson(content[4])
        )

class UpCastE(Exp):
#   | UpCastE of typ * exp                  (* exp as typ *)
    def __init__(self, check_typ, exp):
        self.check_typ = check_typ # typ: Typ
        self.exp = exp # typ: Exp

    def __repr__(self):
        return "p4specast.UpCastE(%r, %r)" % (self.check_typ, self.exp)

    @staticmethod
    def fromjson(content):
        return UpCastE(
            check_typ=Type.fromjson(content[1]),
            exp=Exp.fromjson(content[2]),
        )

class DownCastE(Exp):
#   | DownCastE of typ * exp                (* exp as typ *)
    def __init__(self, check_typ, exp):
        self.check_typ = check_typ # typ: typ
        self.exp = exp # typ: exp

    def __repr__(self):
        return "p4specast.DownCastE(%r, %r)" % (self.check_typ, self.exp)

    @staticmethod
    def fromjson(content):
        return DownCastE(
            check_typ=Type.fromjson(content[1]),
            exp=Exp.fromjson(content[2]),
        )

class SubE(Exp):
#   | SubE of exp * typ                     (* exp `<:` typ *)
    def __init__(self, exp, check_typ):
        self.exp = exp
        self.check_typ = check_typ

    @staticmethod
    def fromjson(content):
        return SubE(
            exp=Exp.fromjson(content[1]),
            check_typ=Type.fromjson(content[2])
        )

    def __repr__(self):
        return "p4specast.SubE(%r, %r)" % (self.exp, self.check_typ)

class MatchE(Exp):
#   | MatchE of exp * pattern               (* exp `matches` pattern *)
    def __init__(self, exp, pattern):
        self.exp = exp
        self.pattern = pattern

    @staticmethod
    def fromjson(content):
        return MatchE(
            exp=Exp.fromjson(content[1]),
            pattern=Pattern.fromjson(content[2])
        )

    def __repr__(self):
        return "p4specast.MatchE(%r, %r)" % (self.exp, self.pattern)

class TupleE(Exp):
#   | TupleE of exp list                    (* `(` exp* `)` *)
    def __init__(self, elts):
        self.elts = elts # typ: exp list

    @staticmethod
    def fromjson(content):
        return TupleE(
            elts=[Exp.fromjson(elt) for elt in content[1].value_array()]
        )

    def __repr__(self):
        return "p4specast.TupleE(%r)" % (self.elts,)

class CaseE(Exp):
#   | CaseE of notexp                       (* notexp *)
    def __init__(self, notexp):
        self.notexp = notexp

    @staticmethod
    def fromjson(content):
        return CaseE(
            notexp=NotExp.fromjson(content[1])
        )

    def __repr__(self):
        return "p4specast.CaseE(%r)" % (self.notexp,)

class StrE(Exp):
#   | StrE of (atom * exp) list             (* { expfield* } *)
    def __init__(self, fields):
        self.fields = fields

    @staticmethod
    def fromjson(content):
        return StrE(
            fields=[(AtomT.fromjson(field[0]), Exp.fromjson(field[1])) for field in content[1].value_array()]
        )

    def __repr__(self):
        return "p4specast.StrE(%r)" % (self.fields,)

class OptE(Exp):
#   | OptE of exp option                    (* exp? *)
    def __init__(self, exp):
        self.exp = exp # typ: Exp | None

    @staticmethod
    def fromjson(content):
        if content[1].is_null:
            return OptE(exp=None)
        return OptE(
            exp=Exp.fromjson(content[1])
        )

    def __repr__(self):
        return "p4specast.OptE(%r)" % (self.exp,)

class ListE(Exp):
#   | ListE of exp list                     (* `[` exp* `]` *)
    def __init__(self, elts):
        self.elts = elts # typ: exp list

    @staticmethod
    def fromjson(content):
        return ListE(
            elts=[Exp.fromjson(elt) for elt in content[1].value_array()]
        )

    def __repr__(self):
        return "p4specast.ListE(%r)" % (self.elts,)

class ConsE(Exp):
#   | ConsE of exp * exp                    (* exp `::` exp *)
    def __init__(self, head, tail):
        self.head = head # typ: exp
        self.tail = tail # typ: exp

    @staticmethod
    def fromjson(content):
        return ConsE(
            head=Exp.fromjson(content[1]),
            tail=Exp.fromjson(content[2])
        )

    def __repr__(self):
        return "p4specast.ConsE(%r, %r)" % (self.head, self.tail)

class CatE(Exp):
#   | CatE of exp * exp                     (* exp `++` exp *)
    def __init__(self, left, right):
        self.left = left # typ: exp
        self.right = right # typ: exp

    @staticmethod
    def fromjson(content):
        return CatE(
            left=Exp.fromjson(content[1]),
            right=Exp.fromjson(content[2])
        )

    def __repr__(self):
        return "p4specast.CatE(%r, %r)" % (self.left, self.right)

class MemE(Exp):
#   | MemE of exp * exp                     (* exp `<-` exp *)
    def __init__(self, elem, lst):
        self.elem = elem # typ: exp
        self.lst = lst # typ: exp

    @staticmethod
    def fromjson(content):
        return MemE(
            elem=Exp.fromjson(content[1]),
            lst=Exp.fromjson(content[2])
        )

    def __repr__(self):
        return "p4specast.MemE(%r, %r)" % (self.elem, self.lst)

class LenE(Exp):
#   | LenE of exp                           (* `|` exp `|` *)
    def __init__(self, lst):
        self.lst = lst # typ: exp

    @staticmethod
    def fromjson(content):
        return LenE(
            lst=Exp.fromjson(content[1])
        )

    def __repr__(self):
        return "p4specast.LenE(%r)" % (self.lst,)

class DotE(Exp):
#   | DotE of exp * atom                    (* exp.atom *)
    def __init__(self, obj, field):
        self.obj = obj # typ: exp
        self.field = field # typ: string

    @staticmethod
    def fromjson(content):
        return DotE(
            obj=Exp.fromjson(content[1]),
            field=AtomT.fromjson(content[2])
        )

    def __repr__(self):
        return "p4specast.DotE(%r, %r)" % (self.obj, self.field)

class IdxE(Exp):
#   | IdxE of exp * exp                     (* exp `[` exp `]` *)
    def __init__(self, lst, idx):
        self.lst = lst # typ: exp
        self.idx = idx # typ: exp

    @staticmethod
    def fromjson(content):
        return IdxE(
            lst=Exp.fromjson(content[1]),
            idx=Exp.fromjson(content[2])
        )

    def __repr__(self):
        return "p4specast.IdxE(%r, %r)" % (self.lst, self.idx)

class SliceE(Exp):
#   | SliceE of exp * exp * exp             (* exp `[` exp `:` exp `]` *)
    def __init__(self, lst, start, stop):
        self.lst = lst # typ: exp
        self.start = start # typ: exp
        self.stop = stop # typ: exp

    @staticmethod
    def fromjson(content):
        return SliceE(
            lst=Exp.fromjson(content[1]),
            start=Exp.fromjson(content[2]),
            stop=Exp.fromjson(content[3])
        )

    def __repr__(self):
        return "p4specast.SliceE(%r, %r, %r)" % (self.lst, self.start, self.stop)

class UpdE(Exp):
#   | UpdE of exp * path * exp              (* exp `[` path `=` exp `]` *)
    def __init__(self, exp, path, value):
        self.exp = exp
        self.path = path
        self.value = value

    @staticmethod
    def fromjson(content):
        return UpdE(
            exp=Exp.fromjson(content[1]),
            path=Path.fromjson(content[2]),
            value=Exp.fromjson(content[3])
        )

    def __repr__(self):
        return "p4specast.UpdE(%r, %r, %r)" % (self.exp, self.path, self.value)

class CallE(Exp):
#   | CallE of id * targ list * arg list    (* $id`<` targ* `>``(` arg* `)` *)
    def __init__(self, func, targs, args):
        self.func = func # typ: Id
        self.targs = targs
        self.args = args # typ: exp list

    @staticmethod
    def fromjson(content):
        return CallE(
            func=Id.fromjson(content[1]),
            targs=[TArg.fromjson(targ) for targ in content[2].value_array()],
            args=[Arg.fromjson(arg) for arg in content[3].value_array()]
        )

    def __repr__(self):
        return "p4specast.CallE(%r, %r, %r)" % (self.func, self.targs, self.args)

class HoldE(Exp):
#   | HoldE of id * notexp                  (* id `:` notexp `holds` *)
    def __init__(self, id, notexp):
        self.id = id
        self.notexp = notexp

    def __repr__(self):
        return "p4specast.HoldE(%r, %r)" % (self.id, self.notexp)

    @staticmethod
    def fromjson(content):
        return HoldE(
            id=Id.fromjson(content[1]),
            notexp=NotExp.fromjson(content[2])
        )

class IterE(Exp):
#   | IterE of exp * iterexp                (* exp iterexp *)
# iterexp = iter * var list
    def __init__(self, exp, iter, varlist):
        self.exp = exp
        self.iter = iter
        self.varlist = varlist

    def __repr__(self):
        return "p4specast.IterE(%r, %r, %r)" % (self.exp, self.iter, self.varlist)

    @staticmethod
    def fromjson(content):
        return IterE(
            exp=Exp.fromjson(content[1]),
            iter=Iter.fromjson(content[2][0]),
            varlist=[Var.fromjson(value) for value in content[2][1].value_array()],
        )

# and notexp = mixop * exp list

class NotExp(AstBase):
    def __init__(self, mixop, exps):
        self.mixop = mixop
        self.exps = exps

    @staticmethod
    def fromjson(content):
        return NotExp(
            mixop=MixOp.fromjson(content[0]),
            exps=[Exp.fromjson(exp) for exp in content[1].value_array()]
        )
    def __repr__(self):
        return "p4specast.NotExp(%s, %s)" % (self.mixop, self.exps)

# and iterexp = iter * var list

class IterExp(AstBase):
    def __init__(self, iter, vars):
        self.iter = iter
        self.vars = vars

    @staticmethod
    def fromjson(content):
        return IterExp(
            iter=Iter.fromjson(content[0]),
            vars=[Var.fromjson(var) for var in content[1].value_array()]
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
    @staticmethod
    def fromjson(value):
        if value.is_object:
            region = Region.fromjson(value['at'])
            content = value['it']
        else:
            region = None
            content = value
        what = content[0].value_string()
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
            raise ValueError("Unknown Type: %s" % what)
        ast.region = region
        return ast

class BoolT(Type):
    def __init__(self):
        pass
    def __repr__(self):
        return "p4specast.BoolT()"

    @staticmethod
    def fromjson(content):
        return BoolT()


class NumT(Type):
    def __init__(self, typ):
        self.typ = typ

    def __repr__(self):
        return "p4specast.NumT(%r)" % (self.typ,)

    @staticmethod
    def fromjson(content):
        return NumT(NumTyp.fromjson(content[1]))


class TextT(Type):
    def __init__(self):
        pass

    def __repr__(self):
        return "p4specast.TextT()"

    @staticmethod
    def fromjson(content):
        return TextT()

class VarT(Type):
    def __init__(self, id, targs):
        self.id = id
        self.targs = targs

    def __repr__(self):
        return "p4specast.VarT(%r, %r)" % (self.id, self.targs)

    @staticmethod
    def fromjson(content):
        return VarT(
            id=Id.fromjson(content[1]),
            targs=[Type.fromjson(targ) for targ in content[2].value_array()]
        )

class TupleT(Type):
    def __init__(self, elts):
        self.elts = elts

    def __repr__(self):
        return "p4specast.TupleT(%r)" % (self.elts,)

    @staticmethod
    def fromjson(content):
        return TupleT(
            elts=[Type.fromjson(elt) for elt in content[1].value_array()]
        )

class IterT(Type):
    def __init__(self, typ, iter):
        self.typ = typ
        self.iter = iter

    def __repr__(self):
        return "p4specast.IterT(%r, %r)" % (self.typ, self.iter)

    @staticmethod
    def fromjson(content):
        return IterT(
            typ=Type.fromjson(content[1]),
            iter=Iter.fromjson(content[2]),
        )

class FuncT(Type):
    def __init__(self):
        pass

    def __repr__(self):
        return "p4specast.FuncT()"

    @staticmethod
    def fromjson(content):
        return FuncT()

# and nottyp = nottyp' phrase
# [@@deriving yojson]
# and nottyp' = mixop * typ list
# [@@deriving yojson]

class NotTyp(AstBase):
    def __init__(self, mixop, typs):
        self.mixop = mixop
        self.typs = typs

    def __repr__(self):
        return "p4specast.NotTyp(%r, %r)" % (self.mixop, self.typs)

    @staticmethod
    def fromjson(value):
        region = Region.fromjson(value['at'])
        content = value['it']
        return NotTyp(
            mixop=MixOp.fromjson(content[0]),
            typs=[Type.fromjson(typ) for typ in content[1].value_array()]
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
        region = Region.fromjson(value['at'])
        content = value['it']
        what = content[0].value_string()
        if what == 'PlainT':
            ast = PlainT.fromjson(content)
        elif what == 'StructT':
            ast = StructT.fromjson(content)
        elif what == 'VariantT':
            ast = VariantT.fromjson(content)
        else:
            raise ValueError("Unknown DefTyp: %s" % what)
        ast.region = region
        return ast

class PlainT(DefTyp):
    def __init__(self, typ):
        self.typ = typ

    @staticmethod
    def fromjson(content):
        return PlainT(
            typ=Type.fromjson(content[1])
        )

    def __repr__(self):
        return "p4specast.PlainT(typ=%s)" % (self.typ,)

class StructT(DefTyp):
    def __init__(self, fields):
        self.fields = fields

    @staticmethod
    def fromjson(content):
        return StructT(
            fields=[TypField.fromjson(field) for field in content[1].value_array()]
        )

    def __repr__(self):
        return "p4specast.StructT(fields=%s)" % (self.fields,)

class VariantT(DefTyp):
    def __init__(self, cases):
        self.cases = cases

    @staticmethod
    def fromjson(content):
        return VariantT(
            cases=[TypeCase.fromjson(case) for case in content[1].value_array()]
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
            name=AtomT.fromjson(content[0]),
            typ=Type.fromjson(content[1])
        )

# and typcase = nottyp

TypeCase = NotTyp

# _____________________________________
# instrs

# and instr = instr' phrase [@@deriving yojson]
# and instr' =
#   | IfI of exp * iterexp list * instr list * phantom option
#   | CaseI of exp * case list * phantom option
#   | OtherwiseI of instr
#   | LetI of exp * exp * iterexp list
#   | RuleI of id * notexp * iterexp list
#   | ResultI of exp list
#   | ReturnI of exp

class Instr(AstBase):
    # has a .region
    @staticmethod
    def fromjson(value):
        assert value['note'].is_null
        region = Region.fromjson(value['at'])
        content = value['it']
        what = content[0].value_string()
        if what == 'IfI':
            ast = IfI.fromjson(content)
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
            raise ValueError("Unknown Instr: %s" % what)
        ast.region = region
        return ast

class IfI(Instr):
    def __init__(self, exp, iters, instrs, phantom, region=None):
        self.exp = exp
        self.iters = iters
        self.instrs = instrs
        self.phantom = phantom
        self.region = region

    @staticmethod
    def fromjson(content):
        return IfI(
            exp=Exp.fromjson(content[1]),
            iters=[IterExp.fromjson(ite) for ite in content[2].value_array()],
            instrs=[Instr.fromjson(instr) for instr in content[3].value_array()],
            phantom=content[4]
        )

    def __repr__(self):
        return "p4specast.IfI(%r, %r, %r, %r%s)" % (self.exp, self.iters, self.instrs, self.phantom, (", " + repr(self.region)) if self.region is not None else '')

class CaseI(Instr):
    def __init__(self, exp, cases, phantom, region=None):
        self.exp = exp
        self.cases = cases
        self.phantom = phantom
        self.region = region

    @staticmethod
    def fromjson(content):
        return CaseI(
            exp=Exp.fromjson(content[1]),
            cases=[Case.fromjson(case) for case in content[2].value_array()],
            phantom=content[3]
        )

    def __repr__(self):
        return "p4specast.CaseI(%r, %r, %r%s)" % (self.exp, self.cases, self.phantom, (", " + repr(self.region)) if self.region is not None else '')

class OtherwiseI(Instr):
    def __init__(self, instr, region=None):
        self.instr = instr
        self.region = region

    @staticmethod
    def fromjson(content):
        return OtherwiseI(
            instr=Instr.fromjson(content[1])
        )

    def __repr__(self):
        return "p4specast.OtherwiseI(%r)" % (self.instr,)

class LetI(Instr):
    def __init__(self, var, value, iters, region=None):
        self.var = var
        self.value = value
        self.iters = iters
        self.region = region

    @staticmethod
    def fromjson(content):
        return LetI(
            var=Exp.fromjson(content[1]),
            value=Exp.fromjson(content[2]),
            iters=[IterExp.fromjson(ite) for ite in content[3].value_array()]
        )

    def __repr__(self):
        return "p4specast.LetI(%r, %r, %r%s)" % (self.var, self.value, self.iters, (", " + repr(self.region)) if self.region is not None else '')

class RuleI(Instr):
    def __init__(self, id, notexp, iters, region=None):
        self.id = id
        self.notexp = notexp
        self.iters = iters
        self.region = region

    @staticmethod
    def fromjson(content):
        return RuleI(
            id=Id.fromjson(content[1]),
            notexp=NotExp.fromjson(content[2]),
            iters=[IterExp.fromjson(ite) for ite in content[3].value_array()]
        )

    def __repr__(self):
        return "p4specast.RuleI(%r, %r, %r%s)" % (self.id, self.notexp, self.iters, (", " + repr(self.region)) if self.region is not None else '')

class ResultI(Instr):
    def __init__(self, exps, region=None):
        self.exps = exps
        self.region = region

    @staticmethod
    def fromjson(content):
        return ResultI(
            exps=[Exp.fromjson(elt) for elt in content[1].value_array()]
        )

    def __repr__(self):
        return "p4specast.ResultI(%r%s)" % (self.exps, (", " + repr(self.region)) if self.region is not None else '')

class ReturnI(Instr):
    def __init__(self, exp, region=None):
        self.exp = exp
        self.region = region

    @staticmethod
    def fromjson(content):
        return ReturnI(
            exp=Exp.fromjson(content[1])
        )

    def __repr__(self):
        return "p4specast.ReturnI(%r%s)" % (self.exp, (", " + repr(self.region)) if self.region is not None else '')


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

    @staticmethod
    def fromjson(content):
        return Case(
            guard=Guard.fromjson(content[0]),
            instrs=[Instr.fromjson(instr) for instr in content[1].value_array()]
        )

    def __repr__(self):
        return "p4specast.Case(%r, %r)" % (self.guard, self.instrs)


class Guard(AstBase):
    @staticmethod
    def fromjson(content):
        kind = content[0].value_string()
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
            raise ValueError("Unknown Guard: %s" % kind)

class BoolG(Guard):
    def __init__(self, value):
        self.value = value # typ: bool

    @staticmethod
    def fromjson(content):
        return BoolG(
            value=content[1].value_bool()
        )

    def __repr__(self):
        return "p4specast.BoolG(%r)" % (self.value,)

class CmpG(Guard):
    def __init__(self, op, typ, exp):
        self.op = op # typ: cmpop
        self.typ = typ # typ: optyp
        self.exp = exp # typ: exp

    @staticmethod
    def fromjson(content):
        return CmpG(
            op=content[1][0].value_string(),
            typ=content[2][0].value_string(),
            exp=Exp.fromjson(content[3])
        )

    def __repr__(self):
        return "p4specast.CmpG(%r, %r, %r)" % (self.op, self.typ, self.exp)

class SubG(Guard):
    def __init__(self, typ):
        self.typ = typ # typ: Type

    @staticmethod
    def fromjson(content):
        return SubG(
            typ=Type.fromjson(content[1])
        )

    def __repr__(self):
        return "p4specast.SubG(%r)" % (self.typ,)

class MatchG(Guard):
    def __init__(self, pattern):
        self.pattern = pattern # typ: Pattern

    @staticmethod
    def fromjson(content):
        return MatchG(
            pattern=Pattern.fromjson(content[1])
        )

    def __repr__(self):
        return "p4specast.MatchG(%r)" % (self.pattern,)

class MemG(Guard):
    def __init__(self, exp):
        self.exp = exp # typ: Exp

    @staticmethod
    def fromjson(content):
        return MemG(
            exp=Exp.fromjson(content[1])
        )

    def __repr__(self):
        return "p4specast.MemG(%r)" % (self.exp,)

# and pattern =
#   | casep of mixop
#   | listp of [ `cons | `fixed of int | `nil ]
#   | optp of [ `some | `none ]

class Pattern(AstBase):
    @staticmethod
    def fromjson(content):
        kind = content[0].value_string()
        if kind == 'CaseP':
            return CaseP.fromjson(content)
        elif kind == 'ListP':
            return ListP.fromjson(content)
        elif kind == 'OptP':
            return OptP.fromjson(content)
        else:
            raise ValueError("Unknown Pattern: %s" % kind)

class CaseP(Pattern):
    def __init__(self, mixop):
        self.mixop = mixop # typ: mixop

    @staticmethod
    def fromjson(content):
        return CaseP(
            mixop=MixOp.fromjson(content[1])
        )

    def __repr__(self):
        return "p4specast.CaseP(%r)" % (self.mixop,)

class ListP(Pattern):
    def __init__(self, element):
        self.element = element # typ: ListPElem

    @staticmethod
    def fromjson(content):
        return ListP(
            element=ListPElem.fromjson(content[1])
        )

    def __repr__(self):
        return "p4specast.ListP(%r)" % (self.element,)

class OptP(Pattern):
    def __init__(self, kind):
        self.kind = kind # "Some" | "None"

    @staticmethod
    def fromjson(content):
        return OptP(
            kind=content[1][0].value_string()
        )

    def __repr__(self):
        return "p4specast.OptP(%r)" % (self.kind,)

# [ `cons | `fixed of int | `nil ]

class ListPElem(AstBase):
    @staticmethod
    def fromjson(content):
        kind = content[0].value_string()
        if kind == 'Cons':
            return Cons()
        elif kind == 'Fixed':
            return Fixed(content[1].value_int())
        elif kind == 'Nil':
            return Nil()
        else:
            raise ValueError("Unknown ListPElem: %s" % kind)

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
    @staticmethod
    def fromjson(value):
        region = Region.fromjson(value['at'])
        content = value['it']
        typ = Type.fromjson(value['note'])
        kind = content[0].value_string()
        if kind == 'RootP':
            ast = RootP()
        elif kind == 'IdxP':
            ast = IdxP.fromjson(content)
        elif kind == 'SliceP':
            ast = SliceP.fromjson(content)
        elif kind == 'DotP':
            ast = DotP.fromjson(content)
        else:
            raise ValueError("Unknown Path: %s" % kind)
        ast.region = region
        ast.typ = typ
        return ast

class RootP(Path):
    @staticmethod
    def fromjson(content):
        return RootP()

    def __repr__(self):
        return "p4specast.RootP()"

class IdxP(Path):
    def __init__(self, path, exp):
        self.path = path
        self.exp = exp

    @staticmethod
    def fromjson(content):
        return IdxP(
            path=Path.fromjson(content[1]),
            exp=Exp.fromjson(content[2])
        )

    def __repr__(self):
        return "p4specast.IdxP(%r, %r)" % (self.path, self.exp)

class SliceP(Path):
    def __init__(self, path, start, end):
        self.path = path
        self.start = start
        self.end = end

    @staticmethod
    def fromjson(content):
        return SliceP(
            path=Path.fromjson(content[1]),
            start=Exp.fromjson(content[2]),
            end=Exp.fromjson(content[3])
        )

    def __repr__(self):
        return "p4specast.SliceP(%r, %r, %r)" % (self.path, self.start, self.end)

class DotP(Path):
    def __init__(self, path, atom):
        self.path = path
        self.atom = atom

    @staticmethod
    def fromjson(content):
        return DotP(
            path=Path.fromjson(content[1]),
            atom=AtomT.fromjson(content[2])
        )

    def __repr__(self):
        return "p4specast.DotP(%r, %r)" % (self.path, self.atom)

# type Mixop.t = Atom.t phrase list list

class MixOp(AstBase):
    def __init__(self, phrases):
        self.phrases = phrases # type: list[list[AtomT]]

    def compare(self, other):
        # type: (MixOp, MixOp) -> int
        """ Compare two MixOp objects lexicographically by their phrases
        Each phrase is a list of AtomT
        Returns -1 if self < other, 0 if equal, 1 if self > other """

        def atom_compare(a, b):
            return a.compare(b)

        def phrase_compare(phrase_a, phrase_b):
            # Compare two lists of AtomT
            len_a = len(phrase_a)
            len_b = len(phrase_b)
            for i in range(min(len_a, len_b)):
                cmp = atom_compare(phrase_a[i], phrase_b[i])
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

    def __repr__(self):
        return "p4specast.MixOp(%r)" % (self.phrases,)

    def __str__(self):
        mixop = self.phrases
        smixop = "%".join(
            ["".join([atom.value for atom in atoms]) for atoms in mixop]
        )
        return "`" + smixop + "`"


class AtomT(AstBase):
    def __init__(self, value, region):
        self.value = value # type: str
        self.region = region # type: Region

    def __repr__(self):
        return "p4specast.AtomT(%r, %r)" % (self.value, self.region)

    def compare(self, other):
        # type: (AtomT, AtomT) -> int
        # TODO: is this right?
        return cmp(self.value, other.value)

    @staticmethod
    def fromjson(value):
        region = Region.fromjson(value['at'])
        content = value['it']
        kind = content[0].value_string()
        if kind == 'Atom':
            return AtomT(
                value=content[1].value_string(),
                region=region
            )
        else:
            return AtomT(
                value=atom_type_to_value(kind),
                region=region
            )

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
