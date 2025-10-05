from rpython.rlib import jit
from rpyp4sp import p4specast
from rpyp4sp.error import P4TypeSubstitutionError
# type theta = t TIdMap.t

# let rec subst_typ (theta : theta) (typ : t) : t =
#   match typ.it with
#   | BoolT | NumT _ | TextT -> typ
#   | VarT (tid, targs) -> (
#       match TIdMap.find_opt tid theta with
#       | Some typ ->
#           if targs <> [] then
#             error_interp typ.at "higher-order substitution is disallowed";
#           typ
#       | None ->
#           let targs = subst_targs theta targs in
#           VarT (tid, targs) $ typ.at)
#   | TupleT typs ->
#       let typs = subst_typs theta typs in
#       TupleT typs $ typ.at
#   | IterT (typ, iter) ->
#       let typ = subst_typ theta typ in
#       IterT (typ, iter) $ typ.at
#   | FuncT -> typ

def make_subst_typ(func):
    @jit.unroll_safe
    def subst_typ(typ, *args):
        if isinstance(typ, p4specast.BoolT) or isinstance(typ, p4specast.NumT) or isinstance(typ, p4specast.TextT):
            return typ
        elif isinstance(typ, p4specast.VarT):
            res = func(typ.id.value, *args)
            if res is not None:
                if typ.targs:
                    raise P4TypeSubstitutionError("higher-order substitution is disallowed")
                return res
            else:
                targs = [subst_typ(targ, *args) for targ in typ.targs]
                return p4specast.VarT(typ.id, targs)
        #import pdb;pdb.set_trace()
        raise P4TypeSubstitutionError("TODO subst_typ: unhandled type %s" % typ.__class__.__name__)
    subst_typ.func_name += '_' + func.func_name
    return subst_typ

def dict_get(name, d):
    return d.get(name)

_subst_typ_dict_key = make_subst_typ(dict_get)

def subst_typ(theta, typ):
    return _subst_typ_dict_key(typ, theta)

def ctx_search(name, ctx):
    a, b = jit.promote(ctx.glbl)._find_typdef(name)
    if a is not None and b is not None:
        deftyp = b
        if isinstance(deftyp, p4specast.PlainT):
            return deftyp.typ
    if ctx.tdenv.has_key(name):
        _, deftyp = ctx.tdenv.get(name)
        if isinstance(deftyp, p4specast.PlainT):
            return deftyp.typ
    return None

_subst_typ_ctx_search = make_subst_typ(ctx_search)
def subst_typ_ctx(ctx, typ):
    return _subst_typ_ctx_search(typ, ctx)

# and subst_typs (theta : theta) (typs : t list) : t list =
#   List.map (subst_typ theta) typs

# and subst_targ (theta : theta) (targ : t) : t = subst_typ theta targ

# and subst_targs (theta : theta) (targs : t list) : t list =
#   List.map (subst_targ theta) targs
