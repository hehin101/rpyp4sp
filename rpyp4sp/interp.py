import pdb
from rpyp4sp import p4specast, objects

class Sign(object):
    # abstract base
    pass

class Cont(Sign):
    pass

class Res(Sign):
    def __init__(self, values):
        self.values = values

class Ret(Sign):
    def __init__(self, value):
        self.value = value

def invoke_func_def_attempt_clauses(ctx, func, values_input):
    # INCOMPLETE
    # and invoke_func_def (ctx : Ctx.t) (id : id) (targs : targ list) (args : arg list) : Ctx.t * value =
    # let tparams, args_input, instrs = Ctx.find_func Local ctx id in
    func = ctx.find_func_local(func.id)
    tparams, args_input, instrs = func.tparams, func.args, func.instrs
    # let ctx_local = Ctx.localize ctx in
    ctx_local = ctx.localize()
    # let ctx_local = Ctx.localize_inputs ctx_local values_input in
    # let ctx_local = assign_args ctx ctx_local args_input values_input in
    ctx_local = assign_args(ctx, ctx_local, args_input, values_input)
    # let ctx_local, sign = eval_instrs ctx_local Cont instrs in
    ctx_local, sign = eval_instrs(ctx_local, Cont(), func.instrs)
    # let ctx = Ctx.commit ctx ctx_local in
    # match sign with
    if isinstance(sign, Ret):
    # | Ret value_output ->
    #     List.iteri
    #       (fun idx_arg value_input ->
    #         Ctx.add_edge ctx value_output value_input
    #           (Dep.Edges.Func (id, idx_arg)))
    #       values_input;
    #     (ctx, value_output)
        return ctx, sign.value
    # | _ -> error id.at "function was not matched"



# ____________________________________________________________
# instructions

def eval_instrs(ctx, sign, instrs):
    #     eval_instrs (ctx : Ctx.t) (sign : Sign.t) (instrs : instr list) :
    #     Ctx.t * Sign.t =
    #   List.fold_left
    #     (fun (ctx, sign) instr ->
    #       match sign with Sign.Cont -> eval_instr ctx instr | _ -> (ctx, sign))
    #     (ctx, sign) instrs
    for instr in instrs:
        if isinstance(sign, Cont):
            ctx, sign = eval_instr(ctx, instr)
        else:
            pass
    return ctx, sign

def eval_instr(ctx, instr):
    # INCOMPLETE
    #     eval_instr (ctx : Ctx.t) (instr : instr) : Ctx.t * Sign.t =
    #   match instr.it with
    #   | IfI (exp_cond, iterexps, instrs_then, phantom_opt) ->
    #       eval_if_instr ctx exp_cond iterexps instrs_then phantom_opt
    if isinstance(instr, p4specast.IfI):
        return eval_if_instr(ctx, instr)
    #   | CaseI (exp, cases, phantom_opt) -> eval_case_instr ctx exp cases phantom_opt
    #   | OtherwiseI instr -> eval_instr ctx instr
    if isinstance(instr, p4specast.OtherwiseI):
        return eval_instr(ctx, instr.instr)
    #   | LetI (exp_l, exp_r, iterexps) -> eval_let_instr ctx exp_l exp_r iterexps
    if isinstance(instr, p4specast.LetI):
        return eval_let_instr(ctx, instr)
    #   | RuleI (id, notexp, iterexps) -> eval_rule_instr ctx id notexp iterexps
    #   | ResultI exps -> eval_result_instr ctx exps
    #   | ReturnI exp -> eval_return_instr ctx exp
    if isinstance(instr, p4specast.ReturnI):
        return eval_return_instr(ctx, instr)
    import pdb; pdb.set_trace()

def eval_if_instr(ctx, instr):
    # INCOMPLETE
    #     eval_if_instr (ctx : Ctx.t) (exp_cond : exp) (iterexps : iterexp list)
    #     (instrs_then : instr list) (phantom_opt : phantom option) : Ctx.t * Sign.t =
    #   let ctx, cond, value_cond = eval_if_cond_iter ctx exp_cond iterexps in
    ctx, cond, value_cond = eval_if_cond_iter(ctx, instr.exp, instr.iters)
    #   let vid = value_cond.note.vid in
    #   let ctx =
    #     match phantom_opt with
    #     | Some (pid, _) -> Ctx.cover ctx (not cond) pid vid
    #     | None -> ctx
    #   in
    #   if cond then eval_instrs ctx Cont instrs_then else (ctx, Cont)
    if cond:
        return eval_instrs(ctx, Cont(), instr.instrs)
    return (ctx, Cont())

def eval_if_cond_iter(ctx, exp_cond, iterexps):
    # let iterexps = List.rev iterexps in
    iterexps = iterexps[::-1]
    # eval_if_cond_iter' ctx exp_cond iterexps
    return eval_if_cond_iter_tick(ctx, exp_cond, iterexps)


def eval_if_cond_iter_tick(ctx, exp_cond, iterexps):
    # INCOMPLETE
    # match iterexps with
    # | [] -> eval_if_cond ctx exp_cond
    if iterexps == []:
        return eval_if_cond(ctx, exp_cond)
    import pdb;pdb.set_trace()
    # | iterexp_h :: iterexps_t -> (
    #     let iter_h, vars_h = iterexp_h in
    #     match iter_h with
    #     | Opt -> error no_region "(TODO)"
    #     | List ->
    #         let ctx, cond, values_cond =
    #           eval_if_cond_list ctx exp_cond vars_h iterexps_t
    #         in
    #         let value_cond =
    #           let vid = Value.fresh () in
    #           let typ = Il.Ast.IterT (Il.Ast.BoolT $ no_region, Il.Ast.List) in
    #           Il.Ast.(ListV values_cond $$$ { vid; typ })
    #         in
    #         Ctx.add_node ctx value_cond;
    #         List.iter
    #           (fun (id, _typ, iters) ->
    #             let value_sub =
    #               Ctx.find_value Local ctx (id, iters @ [ Il.Ast.List ])
    #             in
    #             Ctx.add_edge ctx value_cond value_sub Dep.Edges.Iter)
    #           vars_h;
    #         (ctx, cond, value_cond))


def eval_if_cond(ctx, exp_cond):
    # let ctx, value_cond = eval_exp ctx exp_cond in
    ctx, value_cond = eval_exp(ctx, exp_cond)
    # let cond = Value.get_bool value_cond in
    cond = value_cond.get_bool()
    # (ctx, cond, value_cond)
    return ctx, cond, value_cond

def eval_let_instr(ctx, let_instr):
    # let ctx = eval_let_iter ctx exp_l exp_r iterexps in
    # (ctx, Cont)
    ctx = eval_let_iter(ctx, let_instr)
    return ctx, Cont()

def eval_let_iter_tick(ctx, exp_l, exp_r, iterexps):
    # INCOMPLETE
    # match iterexps with
    # | [] -> eval_let ctx exp_l exp_r
    if iterexps == []:
        return eval_let(ctx, exp_l, exp_r)
    # | iterexp_h :: iterexps_t -> (
    #     let iter_h, vars_h = iterexp_h in
    #     match iter_h with
    #     | Opt -> eval_let_opt ctx exp_l exp_r vars_h iterexps_t
    #     | List -> eval_let_list ctx exp_l exp_r vars_h iterexps_t)
    import pdb;pdb.set_trace()

def eval_let_iter(ctx, let_instr):
    # let iterexps = List.rev iterexps in
    iterexps = let_instr.iters[::-1]
    # eval_let_iter' ctx exp_l exp_r iterexps
    return eval_let_iter_tick(ctx, let_instr.var, let_instr.value, iterexps)

def eval_let(ctx, exp_l, exp_r):
    # let ctx, value = eval_exp ctx exp_r in
    ctx, value = eval_exp(ctx, exp_r)
    # assign_exp ctx exp_l value
    return assign_exp(ctx, exp_l, value)

def assign_exp(ctx, exp, value):
    # INCOMPLETE
    # let note = value.note.typ in
    # match (exp.it, value.it) with
    if isinstance(exp, p4specast.VarE):
    # | VarE id, _ ->
    #     let ctx = Ctx.add_value Local ctx (id, []) value in
        ctx = ctx.add_value_local(exp.id, [], value)
        return ctx
    #     ctx
    # | TupleE exps_inner, TupleV values_inner ->
    #     let ctx = assign_exps ctx exps_inner values_inner in
    #     List.iter
    #       (fun value_inner -> Ctx.add_edge ctx value_inner value Dep.Edges.Assign)
    #       values_inner;
    #     ctx
    # | CaseE notexp, CaseV (_mixop_value, values_inner) ->
    #     let _mixop_exp, exps_inner = notexp in
    #     let ctx = assign_exps ctx exps_inner values_inner in
    #     List.iter
    #       (fun value_inner -> Ctx.add_edge ctx value_inner value Dep.Edges.Assign)
    #       values_inner;
    #     ctx
    elif isinstance(exp, p4specast.CaseE) and\
        isinstance(value, objects.W_CaseV):
            notexp = exp.notexp
            mixop_exp, exps_inner = notexp.mixop, notexp.exps
            values_inner = value.values
            ctx = assign_exps(ctx, exps_inner, values_inner)
            # for value_inner in values_inner:
            #    assert False, "ctx.add_edge(ctx, value_inner, value, dep.edges.Assign)"
            return ctx
    import pdb;pdb.set_trace()
    # | OptE exp_opt, OptV value_opt -> (
    #     match (exp_opt, value_opt) with
    #     | Some exp_inner, Some value_inner ->
    #         let ctx = assign_exp ctx exp_inner value_inner in
    #         Ctx.add_edge ctx value_inner value Dep.Edges.Assign;
    #         ctx
    #     | None, None -> ctx
    #     | _ -> assert false)
    # | ListE exps_inner, ListV values_inner ->
    #     let ctx = assign_exps ctx exps_inner values_inner in
    #     List.iter
    #       (fun value_inner -> Ctx.add_edge ctx value_inner value Dep.Edges.Assign)
    #       values_inner;
    #     ctx
    # | ConsE (exp_h, exp_t), ListV values_inner ->
    #     let value_h = List.hd values_inner in
    #     let value_t =
    #       let vid = Value.fresh () in
    #       let typ = note in
    #       Il.Ast.(ListV (List.tl values_inner) $$$ { vid; typ })
    #     in
    #     Ctx.add_node ctx value_t;
    #     let ctx = assign_exp ctx exp_h value_h in
    #     Ctx.add_edge ctx value_h value Dep.Edges.Assign;
    #     let ctx = assign_exp ctx exp_t value_t in
    #     Ctx.add_edge ctx value_t value Dep.Edges.Assign;
    #     ctx
    # | IterE (_, (Opt, vars)), OptV None ->
    #     (* Per iterated variable, make an option out of the value *)
    #     List.fold_left
    #       (fun ctx (id, typ, iters) ->
    #         let value_sub =
    #           let vid = Value.fresh () in
    #           let typ = Typ.iterate typ (iters @ [ Il.Ast.Opt ]) in
    #           Il.Ast.(OptV None $$$ { vid; typ = typ.it })
    #         in
    #         Ctx.add_node ctx value_sub;
    #         Ctx.add_edge ctx value_sub value Dep.Edges.Assign;
    #         Ctx.add_value Local ctx (id, iters @ [ Il.Ast.Opt ]) value_sub)
    #       ctx vars
    # | IterE (exp, (Opt, vars)), OptV (Some value) ->
    #     (* Assign the value to the iterated expression *)
    #     let ctx = assign_exp ctx exp value in
    #     (* Per iterated variable, make an option out of the value *)
    #     List.fold_left
    #       (fun ctx (id, typ, iters) ->
    #         let value_sub =
    #           let value = Ctx.find_value Local ctx (id, iters) in
    #           let vid = Value.fresh () in
    #           let typ = Typ.iterate typ (iters @ [ Il.Ast.Opt ]) in
    #           Il.Ast.(OptV (Some value) $$$ { vid; typ = typ.it })
    #         in
    #         Ctx.add_node ctx value_sub;
    #         Ctx.add_edge ctx value_sub value Dep.Edges.Assign;
    #         Ctx.add_value Local ctx (id, iters @ [ Il.Ast.Opt ]) value_sub)
    #       ctx vars
    # | IterE (exp, (List, vars)), ListV values ->
    #     (* Map over the value list elements,
    #        and assign each value to the iterated expression *)
    #     let ctxs =
    #       List.fold_left
    #         (fun ctxs value ->
    #           let ctx =
    #             { ctx with local = { ctx.local with venv = VEnv.empty } }
    #           in
    #           let ctx = assign_exp ctx exp value in
    #           ctxs @ [ ctx ])
    #         [] values
    #     in
    #     (* Per iterated variable, collect its elementwise value,
    #        then make a sequence out of them *)
    #     List.fold_left
    #       (fun ctx (id, typ, iters) ->
    #         let values =
    #           List.map (fun ctx -> Ctx.find_value Local ctx (id, iters)) ctxs
    #         in
    #         let value_sub =
    #           let vid = Value.fresh () in
    #           let typ = Typ.iterate typ (iters @ [ Il.Ast.List ]) in
    #           Il.Ast.(ListV values $$$ { vid; typ = typ.it })
    #         in
    #         Ctx.add_node ctx value_sub;
    #         Ctx.add_edge ctx value_sub value Dep.Edges.Assign;
    #         Ctx.add_value Local ctx (id, iters @ [ Il.Ast.List ]) value_sub)
    #       ctx vars
    # | _ ->
    #     error exp.at
    #       (F.asprintf "(TODO) match failed %s <- %s"
    #          (Sl.Print.string_of_exp exp)
    #          (Sl.Print.string_of_value ~short:true value))

def assign_exps(ctx, exps, values):
    #assign_exps (ctx : Ctx.t) (exps : exp list) (values : value list) : Ctx.t =
    #   check
    #     (List.length exps = List.length values)
    #     (over_region (List.map at exps))
    #     (F.asprintf
    #        "mismatch in number of expressions and values while assigning, expected \
    #         %d value(s) but got %d"
    #        (List.length exps) (List.length values));
    #   List.fold_left2 assign_exp ctx exps values
    assert len(exps) == len(values), "mismatch in number of expressions and values while assigning, expected %d value(s) but got %d" % (len(exps), len(values))
    for (exp, value) in zip(exps, values):
        ctx = assign_exp(ctx, exp, value)
    return ctx


#and assign_arg (ctx_caller : Ctx.t) (ctx_callee : Ctx.t) (arg : arg)
#    (value : value) : Ctx.t =
#  match arg.it with
#  | ExpA exp -> assign_arg_exp ctx_callee exp value
#  | DefA id -> assign_arg_def ctx_caller ctx_callee id value
def assign_arg(ctx_caller, ctx_callee, arg, value):
    if isinstance(arg, p4specast.ExpA):
        return assign_arg_exp(ctx_callee, arg.exp, value)
    elif isinstance(arg, p4specast.DefA):
        return assign_arg_def(ctx_caller, ctx_callee, arg.id, value)
    else:
        assert False, "invalid type of arg " + str(arg)

#and assign_args (ctx_caller : Ctx.t) (ctx_callee : Ctx.t) (args : arg list)
#    (values : value list) : Ctx.t =
#  check
#    (List.length args = List.length values)
#    (over_region (List.map at args))
#    (F.asprintf
#       "mismatch in number of arguments and values while assigning, expected \
#        %d value(s) but got %d"
#       (List.length args) (List.length values));
#  List.fold_left2 (assign_arg ctx_caller) ctx_callee args values

def assign_args(ctx_caller, ctx_callee, args, values):
    assert len(args) == len(values), \
        "mismatch in number of arguments while assigning, expected %d value(s) but got %d" (len(args), len(values))
    for arg, value in zip(args, values):
        ctx_callee = assign_arg(ctx_caller, ctx_callee, arg, value)
    return ctx_callee

# and assign_arg_exp (ctx : Ctx.t) (exp : exp) (value : value) : Ctx.t =
#   assign_exp ctx exp value
assign_arg_exp = assign_exp

# and assign_arg_def (ctx_caller : Ctx.t) (ctx_callee : Ctx.t) (id : id)
#     (value : value) : Ctx.t =
#   match value.it with
#   | FuncV id_f ->
#       let func = Ctx.find_func Local ctx_caller id_f in
#       Ctx.add_func Local ctx_callee id func
#   | _ ->
#       error id.at
#         (F.asprintf "cannot assign a value %s to a definition %s"
#            (Sl.Print.string_of_value ~short:true value)
#            id.it)
def assign_arg_def(ctx_caller, ctx_callee, id, value):
    if isinstance(value, objects.W_FuncV):
        func = ctx_caller.find_func_local(value.id)
        import pdb; pdb.set_trace()
        ctx_callee.add_func_local(id, func)
        return ctx_callee
    else:
        assert False, "cannot assign a value %s to a definition %s" % (
            str(value), str(id))


def eval_return_instr(ctx, instr):
    # let ctx, value = eval_exp ctx exp in
    # (ctx, Ret value)
    ctx, value = eval_exp(ctx, instr.exp)
    return (ctx, Ret(value))

# ____________________________________________________________
# expressions

def eval_exp(ctx, exp):
    return exp.eval_exp(ctx)

class __extend__(p4specast.Exp):
    def eval_exp(self, ctx):
        import pdb;pdb.set_trace()
        raise NotImplementedError("abstract base class")

class __extend__(p4specast.BoolE):
    def eval_exp(self, ctx):
        # let value_res =
        #   let vid = Value.fresh () in
        #   let typ = note in
        #   Il.Ast.(BoolV b $$$ { vid; typ })
        # in
        # Ctx.add_node ctx value_res;
        # List.iter
        #   (fun value_input ->
        #     Ctx.add_edge ctx value_res value_input Dep.Edges.Control)
        #   ctx.local.values_input;
        # (ctx, value_res)
        return ctx, objects.W_BoolV(self.value, typ=self.typ)

class __extend__(p4specast.VarE):
    def eval_exp(self, ctx):
        # let value = Ctx.find_value Local ctx (id, []) in
        value = ctx.find_value_local(self.id, [])
        return ctx, value

class __extend__(p4specast.SubE):
    def eval_exp(self, ctx):
        typ = self.check_typ
        note = self.typ
        # let ctx, value = eval_exp ctx exp in
        ctx, value = eval_exp(ctx, self.exp)
        # let sub = subtyp ctx typ value in
        sub = subtyp(ctx, typ, value)
        # let value_res =
        #   let vid = Value.fresh () in
        #   let typ = note in
        #   Il.Ast.(BoolV sub $$$ { vid; typ })
        value_res = objects.W_BoolV(sub, typ=note)
        # in
        # Ctx.add_node ctx value_res;
        # Ctx.add_edge ctx value_res value (Dep.Edges.Op (SubOp typ));
        # (ctx, value_res)
        return ctx, value_res

class __extend__(p4specast.DownCastE):
    def eval_exp(self, ctx):
        # let ctx, value = eval_exp ctx exp in
        ctx, value = eval_exp(ctx, self.exp)
        # let ctx, value_res = downcast ctx typ value in
        # (ctx, value_res)
        return downcast(ctx, self.check_typ, value)

class __extend__(p4specast.MatchE):
    def eval_exp(self, ctx):
        # INCOMPLETE
        # let ctx, value = eval_exp ctx exp in
        ctx, value = eval_exp(ctx, self.exp)
        # let matches =
        #   match (pattern, value.it) with
        if (isinstance(self.pattern, p4specast.CaseP) and
                isinstance(value, objects.W_CaseV)):
            matches = mixop_eq(self.pattern.mixop, value.mixop)
        #   | CaseP mixop_p, CaseV (mixop_v, _) -> Mixop.eq mixop_p mixop_v
        else:
            import pdb;pdb.set_trace()
        #   | ListP listpattern, ListV values -> (
        #       let len_v = List.length values in
        #       match listpattern with
        #       | `Cons -> len_v > 0
        #       | `Fixed len_p -> len_v = len_p
        #       | `Nil -> len_v = 0)
        #   | OptP `Some, OptV (Some _) -> true
        #   | OptP `None, OptV None -> true
        #   | _ -> false
        # in
        # let value_res =
        #   let vid = Value.fresh () in
        #   let typ = note in
        #   Il.Ast.(BoolV matches $$$ { vid; typ })
        value_res = objects.W_BoolV(matches, typ=self.typ)
        # in
        # Ctx.add_node ctx value_res;
        # Ctx.add_edge ctx value_res value (Dep.Edges.Op (MatchOp pattern));
        # (ctx, value_res)
        return ctx, value_res

# ____________________________________________________________

def subtyp(ctx, typ, value):
    # INCOMPLETE
    # match typ.it with
    # | NumT `NatT -> (
    #     match value.it with
    #     | NumV (`Nat _) -> true
    #     | NumV (`Int i) -> Bigint.(i >= zero)
    #     | _ -> assert false)
    # | VarT (tid, targs) -> (
    if isinstance(typ, p4specast.VarT):
    #     let tparams, deftyp = Ctx.find_typdef Local ctx tid in
        tparams, deftyp = ctx.find_typdef_local(typ.id)
    #     let theta = List.combine tparams targs |> TIdMap.of_list in
        assert tparams == []
        assert typ.targs == []
        if isinstance(deftyp, p4specast.PlainT):
            import pdb;pdb.set_trace()
    #     match (deftyp.it, value.it) with
    #     | PlainT typ, _ ->
    #         let typ = Typ.subst_typ theta typ in
    #         subtyp ctx typ value
    #     | VariantT typcases, CaseV (mixop_v, _) ->
        if (isinstance(deftyp, p4specast.VariantT) and
                isinstance(value, objects.W_CaseV)):
            for nottyp in deftyp.cases:
                if mixop_eq(nottyp.mixop, value.mixop):
                    return True
            else:
                return False
    #         List.exists
    #           (fun nottyp ->
    #             let mixop_t, _ = nottyp.it in
    #             Mixop.eq mixop_t mixop_v)
    #           typcases
    #     | _ -> true)
    import pdb;pdb.set_trace()

    # | TupleT typs -> (
    #     match value.it with
    #     | TupleV values ->
    #         List.length typs = List.length values
    #         && List.for_all2 (subtyp ctx) typs values
    #     | _ -> false)
    # | _ -> true

def downcast(ctx, typ, value):
    # INCOMPLETE
    # match typ.it with
    # | NumT `NatT -> (
    if isinstance(typ, p4specast.NumT):
        import pdb;pdb.set_trace()
    #     match value.it with
    #     | NumV (`Nat _) -> (ctx, value)
    #     | NumV (`Int i) when Bigint.(i >= zero) ->
    #         let value_res =
    #           let vid = Value.fresh () in
    #           let typ = typ.it in
    #           Il.Ast.(NumV (`Nat i) $$$ { vid; typ })
    #         in
    #         Ctx.add_node ctx value_res;
    #         Ctx.add_edge ctx value_res value (Dep.Edges.Op (CastOp typ));
    #         (ctx, value_res)
    #     | _ -> assert false)
    # | VarT (tid, targs) -> (
    if isinstance(typ, p4specast.VarT):
        tparams, deftyp = ctx.find_typdef_local(typ.id)
        assert tparams == []
    #     let tparams, deftyp = Ctx.find_typdef Local ctx tid in
    #     let theta = List.combine tparams targs |> TIdMap.of_list in
    #     match deftyp.it with
    #     | PlainT typ ->
        if isinstance(deftyp, p4specast.PlainT):
            import pdb;pdb.set_trace()
    #         let typ = Typ.subst_typ theta typ in
    #         downcast ctx typ value
    #     | _ -> (ctx, value))
        else:
            return ctx, value
    # | TupleT typs -> (
    if isinstance(typ, p4specast.TupleT):
        import pdb;pdb.set_trace()
    #     match value.it with
    #     | TupleV values ->
    #         let ctx, values =
    #           List.fold_left2
    #             (fun (ctx, values) typ value ->
    #               let ctx, value = downcast ctx typ value in
    #               (ctx, values @ [ value ]))
    #             (ctx, []) typs values
    #         in
    #         let value_res =
    #           let vid = Value.fresh () in
    #           let typ = typ.it in
    #           Il.Ast.(TupleV values $$$ { vid; typ })
    #         in
    #         Ctx.add_node ctx value_res;
    #         Ctx.add_edge ctx value_res value (Dep.Edges.Op (CastOp typ));
    #         (ctx, value_res)
    #     | _ -> assert false)
    # | _ -> (ctx, value)
    return ctx, value


def mixop_eq(a, b):
    phrasesa = a.phrases
    phrasesb = b.phrases
    if len(phrasesa) != len(phrasesb):
        return False
    for suba, subb in zip(phrasesa, phrasesb):
        if len(suba) != len(subb):
            return False
        for atoma, atomb in zip(suba, subb):
            if atoma.value != atomb.value:
                return False
    return True
