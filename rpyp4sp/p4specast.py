
class AstBase(object):
    def __eq__(self, other):
        return type(self) == type(other) and self.__dict__ == other.__dict__


# type pos = { file : string; line : int; column : int } [@@deriving yojson]
# type region = { left : pos; right : pos } [@@deriving yojson]

class Position(AstBase):
    def __init__(self, file, line, column):
        self.file = file # type: str
        self.line = line # type: int
        self.column = column # type: int

    @staticmethod
    def fromjson(value):
        return Position(value['file'], value['line'], value['column'])
    
    def __repr__(self):
        return "Position(file=%s, line=%d, column=%d)" % (self.file, self.line, self.column)


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

    def __repr__(self):
        return "Region(left=%s, right=%s)" % (self.left, self.right)

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
        assert isinstance(value, dict)
        region = Region.fromjson(value['at'])
        return Id(
            value["it"],
            region
        )

    def __repr__(self):
        return "Id(value=%s, region=%s)" % (self.value, self.region)


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
        assert isinstance(value, list)
        what = value[0]
        if what == 'DecD':
            return DecD.fromjson(value)
        elif what == 'TypD':
            return TypD.fromjson(value)
        elif what == 'RelD':
            return RelD.fromjson(value)


class TypD(Def):
    def __init__(self, id, tparams, deftyp):
        self.id = id            # type: Id
        self.tparams = tparams  # type: list[tparam]
        self.deftyp = deftyp    # type: deftyp

    @staticmethod
    def fromjson(value):
        _, id, tparams_value, deftype_value = value
        tparams = [TParam.fromjson(p) for p in tparams_value]
        deftype = DefType.fromjson(deftype_value)
        return TypD(
            id=Id.fromjson(id),
            tparams=tparams,
            deftype=deftype
        )


class RelD(Def):
    def __init__(self, id, mixop, hints, exps, instrs):
        self.id = id            # type: Id
        self.mixop = mixop      # type: mixop
        self.hints = hints      # type: list[hint]
        self.exps = exps        # type: list[exp]
        self.instrs = instrs    # type: list[instr]

    @staticmethod
    def fromjson(value):
        _, id, mixop, hints_value, exps_value, instrs_value = value
        hints = [Hint.fromjson(h) for h in hints_value]
        exps = [Exp.fromjson(e) for e in exps_value]
        instrs = [Instr.fromjson(i) for i in instrs_value]
        return RelD(
            id=Id.fromjson(id),
            mixop=mixop,
            hints=hints,
            exps=exps,
            instrs=instrs
        )

class DecD(Def):
    def __init__(self, id, tparams, args, instrs):
        self.id = id            # type: Id
        self.tparams = tparams  # type: list[tparam]
        self.args = args        # type: list[arg]
        self.instrs = instrs    # type: list[instr]

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