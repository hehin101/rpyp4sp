from rpyp4sp import p4specast
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

def subst_typ(theta, typ):
    if isinstance(typ, p4specast.BoolT) or isinstance(typ, p4specast.NumT) or isinstance(typ, p4specast.TextT):
        return typ
    elif isinstance(typ, p4specast.VarT):
        res = theta.get(typ.id.value, None)
        if res is not None:
            if typ.targs:
                raise ValueError("higher-order substitution is disallowed")
            return res
        else:
            targs = [subst_typ(theta, targ) for targ in typ.targs]
            return p4specast.VarT(typ.id, targs)
    import pdb;pdb.set_trace()
    assert 0, "TODO subst_typ"

# and subst_typs (theta : theta) (typs : t list) : t list =
#   List.map (subst_typ theta) typs

# and subst_targ (theta : theta) (targ : t) : t = subst_typ theta targ

# and subst_targs (theta : theta) (targs : t list) : t list =
#   List.map (subst_targ theta) targs
