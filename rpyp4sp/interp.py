import pdb
from rpyp4sp import p4specast, objects, builtin, context, integers

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


def invoke_func(ctx, calle):
    # if Builtin.is_builtin id then invoke_func_builtin ctx id targs args
    if builtin.is_builtin(calle.func.value):
        return invoke_func_builtin(ctx, calle)
    # else invoke_func_def ctx id targs args
    return invoke_func_def(ctx, calle)

def invoke_func_builtin(ctx, calle):
    # let ctx, values_input = eval_args ctx args in
    ctx, values_input = eval_args(ctx, calle.args)
    # let value_output = Builtin.invoke ctx id targs values_input in
    value_output = builtin.invoke(ctx, calle.func, calle.targs, values_input)
    # List.iteri
    #   (fun idx_arg value_input ->
    #     Ctx.add_edge ctx value_output value_input (Dep.Edges.Func (id, idx_arg)))
    #   values_input;
    # (ctx, value_output)
    return ctx, value_output

def invoke_func_def(ctx, calle):
    # let tparams, args_input, instrs = Ctx.find_func Local ctx id in
    func = ctx.find_func_local(calle.func)
    # check (instrs <> []) id.at "function has no instructions";
    assert func.instrs
    # let ctx_local = Ctx.localize ctx in
    ctx_local = ctx.localize()
    # check
    #   (List.length targs = List.length tparams)
    #   id.at "arity mismatch in type arguments";
    assert len(calle.targs) == len(func.tparams), "arity mismatch in type arguments"
    assert calle.targs == [], "TODO"
    # let targs =
    #   let theta =
    #     TDEnv.bindings ctx.global.tdenv @ TDEnv.bindings ctx.local.tdenv
    #     |> List.filter_map (fun (tid, (_tparams, deftyp)) ->
    #            match deftyp.it with
    #            | Il.Ast.PlainT typ -> Some (tid, typ)
    #            | _ -> None)
    #     |> TIdMap.of_list
    #   in
    #   List.map (Typ.subst_typ theta) targs
    # in
    # let ctx_local =
    #   List.fold_left2
    #     (fun ctx_local tparam targ ->
    #       Ctx.add_typdef Local ctx_local tparam ([], Il.Ast.PlainT targ $ targ.at))
    #     ctx_local tparams targs
    # in
    # let ctx, values_input = eval_args ctx args in
    ctx, values_input = eval_args(ctx, calle.args)
    return invoke_func_def_attempt_clauses(ctx, func, values_input)

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
    import pdb; pdb.set_trace()
    assert 0, "TODO invoke_func_def_attempt_clauses"

def eval_arg(ctx, arg):
    # INCOMPLETE
    # match arg.it with
    # | ExpA exp -> eval_exp ctx exp
    if isinstance(arg, p4specast.ExpA):
        res = eval_exp(ctx, arg.exp)
        if res is not None:
            return res

    # | DefA id ->
    #     let value_res =
    #       let vid = Value.fresh () in
    #       let typ = Il.Ast.FuncT in
    #       Il.Ast.(FuncV id $$$ { vid; typ })
    #     in
    #     Ctx.add_node ctx value_res;
    #     (ctx, value_res)
    import pdb;pdb.set_trace()
    assert 0, "TODO eval_arg"

def eval_args(ctx, args):
    # List.fold_left
    #   (fun (ctx, values) arg ->
    #     let ctx, value = eval_arg ctx arg in
    #     (ctx, values @ [ value ]))
    #   (ctx, []) args
    values = []
    for arg in args:
        ctx, value = eval_arg(ctx, arg)
        values.append(value)
    return ctx, values

# ____________________________________________________________
# relations


def invoke_rel(ctx, id, values_input):
    # returns (Ctx.t * value list) option =

    # let _inputs, exps_input, instrs = Ctx.find_rel Local ctx id in
    reld = ctx.find_rel_local(id)
    # check (instrs <> []) id.at "relation has no instructions";
    # let attempt_rules () =
    #   let ctx_local = Ctx.localize ctx in
    ctx_local = ctx.localize()
    #   let ctx_local = Ctx.localize_inputs ctx_local values_input in
    ctx_local = ctx_local.localize_inputs(values_input)
    #   let ctx_local = assign_exps ctx_local exps_input values_input in
    ctx_local = assign_exps(ctx_local, reld.exps, values_input)
    #   let ctx_local, sign = eval_instrs ctx_local Cont instrs in
    ctx_local, sign = eval_instrs(ctx_local, Cont(), reld.instrs)
    ctx = ctx.commit(ctx_local)
    #   let ctx = Ctx.commit ctx ctx_local in
    #   match sign with
    #   | Res values_output ->
    if isinstance(sign, Res):
        return ctx, sign.values
    #       List.iteri
    #         (fun idx_arg value_input ->
    #           List.iter
    #             (fun value_output ->
    #               Ctx.add_edge ctx value_output value_input
    #                 (Dep.Edges.Rel (id, idx_arg)))
    #             values_output)
    #         values_input;
    #       Some (ctx, values_output)
    else:
        return None, None
    #   | _ -> None
    # in
    # if (not ctx.derive) && Cache.is_cached_rule id.it then (
    #   let cache_result = Cache.Cache.find_opt !rule_cache (id.it, values_input) in
    #   match cache_result with
    #   | Some values_output -> Some (ctx, values_output)
    #   | None ->
    #       let* ctx, values_output = attempt_rules () in
    #       Cache.Cache.add !rule_cache (id.it, values_input) values_output;
    #       Some (ctx, values_output))
    # else attempt_rules ()

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
            assert sign is not Cont
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
    if isinstance(instr, p4specast.CaseI):
        return eval_case_instr(ctx, instr)
    #   | OtherwiseI instr -> eval_instr ctx instr
    if isinstance(instr, p4specast.OtherwiseI):
        return eval_instr(ctx, instr.instr)
    #   | LetI (exp_l, exp_r, iterexps) -> eval_let_instr ctx exp_l exp_r iterexps
    if isinstance(instr, p4specast.LetI):
        return eval_let_instr(ctx, instr)
    #   | RuleI (id, notexp, iterexps) -> eval_rule_instr ctx id notexp iterexps
    if isinstance(instr, p4specast.RuleI):
        return eval_rule_instr(ctx, instr)
    #   | ResultI exps -> eval_result_instr ctx exps
    if isinstance(instr, p4specast.ResultI):
        return eval_result_instr(ctx, instr)
    #   | ReturnI exp -> eval_return_instr ctx exp
    if isinstance(instr, p4specast.ReturnI):
        return eval_return_instr(ctx, instr)
    import pdb; pdb.set_trace()
    assert 0, "TODO eval_instr"

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

def eval_if_cond_list(ctx, exp_cond, vars, iterexps):
    #   let ctxs_sub = Ctx.sub_list ctx vars in
    #   List.fold_left
    #     (fun (ctx, cond, values_cond) ctx_sub ->
    #       if not cond then (ctx, cond, values_cond)
    #       else
    #         let ctx_sub, cond, value_cond =
    #           eval_if_cond_iter' ctx_sub exp_cond iterexps
    #         in
    #         let ctx = Ctx.commit ctx ctx_sub in
    #         let values_cond = values_cond @ [ value_cond ] in
    #         (ctx, cond, values_cond))
    #     (ctx, true, []) ctxs_sub
    ctxs_sub = ctx.sub_list(vars)
    cond = True
    values_cond = []
    for ctx_sub in ctxs_sub:
        if not cond:
            break
        ctx_sub, cond, value_cond = eval_if_cond_iter_tick(ctx_sub, exp_cond, iterexps)
        ctx = ctx.commit(ctx_sub)
        values_cond.append(value_cond)
    return ctx, cond, values_cond

def eval_if_cond_iter_tick(ctx, exp_cond, iterexps):
    # INCOMPLETE
    # match iterexps with
    # | [] -> eval_if_cond ctx exp_cond
    if iterexps == []:
        return eval_if_cond(ctx, exp_cond)
    else:
    # | iterexp_h :: iterexps_t -> (
    #     let iter_h, vars_h = iterexp_h in
        iterexp = iterexps[0]
        iterexps_t = iterexps[1:]
        iter_h = iterexp.iter
        vars_h = iterexp.vars
    #     match iter_h with
    #     | Opt -> error no_region "(TODO)"
        if isinstance(iter_h, p4specast.Opt):
            assert 0, "not implemented in p4-spectec yet"
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
        elif isinstance(iter_h, p4specast.List):
            ctx, cond, values_cond = eval_if_cond_list(ctx, exp_cond, vars_h, iterexps_t)
            typ = p4specast.IterT(p4specast.BoolT(), p4specast.List())
            value_cond = objects.ListV(values_cond, typ=typ)
            return ctx, cond, value_cond
    assert 0, "TODO eval_if_cond_iter_tick"

def eval_if_cond(ctx, exp_cond):
    # let ctx, value_cond = eval_exp ctx exp_cond in
    ctx, value_cond = eval_exp(ctx, exp_cond)
    # let cond = Value.get_bool value_cond in
    cond = value_cond.get_bool()
    # (ctx, cond, value_cond)
    return ctx, cond, value_cond

def eval_cases(ctx, exp, cases):
    # returns  Ctx.t * instr list option * value =
    # cases
    block_match = None
    values_cond = []
    # |> List.fold_left
    for case in cases:
        #  (fun (ctx, block_match, values_cond) (guard, block) ->
        #    match block_match with
        #    | Some _ -> (ctx, block_match, values_cond)
        if block_match is not None:
            continue
        #    | None ->
    #            let exp_cond =
    #              match guard with
        guard = case.guard
        #          | BoolG true -> exp.it
        if isinstance(guard, p4specast.BoolG):
            exp_cond = exp
        #          | BoolG false -> Il.Ast.UnE (`NotOp, `BoolT, exp)
        #          | CmpG (cmpop, optyp, exp_r) ->
        #              Il.Ast.CmpE (cmpop, optyp, exp, exp_r)
        elif isinstance(guard, p4specast.CmpG):
            exp_cond = p4specast.CmpE(guard.op, guard.typ, exp, guard.exp)
        #          | SubG typ -> Il.Ast.SubE (exp, typ)
        elif isinstance(guard, p4specast.SubG):
            exp_cond = p4specast.SubE(exp, guard.typ)
        #          | MatchG pattern -> Il.Ast.MatchE (exp, pattern)
        elif isinstance(guard, p4specast.MatchG):
            exp_cond = p4specast.MatchE(exp, guard.pattern)
        #          | MemG exp_s -> Il.Ast.MemE (exp, exp_s)
        elif isinstance(guard, p4specast.MemG):
            exp_cond = p4specast.MemE(exp, guard.exp)
        else:
            import pdb;pdb.set_trace()
            assert 0, 'missing case'
        exp_cond.typ = p4specast.BoolT()

        #        in
        #        let exp_cond = exp_cond $$ (exp.at, Il.Ast.BoolT) in
        #        let ctx, value_cond = eval_exp ctx exp_cond in
        ctx, value_cond = eval_exp(ctx, exp_cond)
        #        let values_cond = values_cond @ [ value_cond ] in
        values_cond.append(values_cond)
        #        let cond = Value.get_bool value_cond in
        cond = value_cond.get_bool()
        #        if cond then (ctx, Some block, values_cond)
        if cond:
            block_match = case.instrs
        #        else (ctx, None, values_cond))
        else:
            assert block_match is None
    #      (ctx, None, [])
    # |> fun (ctx, block_match, values_cond) ->
    # let value_cond =
    #   let vid = Value.fresh () in
    #   let typ = Il.Ast.IterT (Il.Ast.BoolT $ no_region, Il.Ast.List) in
    #   Il.Ast.(ListV values_cond $$$ { vid; typ })
    value_cond = None # INCOMPLETE
    # in
    # Ctx.add_node ctx value_cond;
    # (ctx, block_match, value_cond)
    return ctx, block_match, value_cond

def eval_case_instr(ctx, case_instr):
    # let ctx, instrs_opt, value_cond = eval_cases ctx exp cases in
    ctx, instrs_opt, value_cond = eval_cases(ctx, case_instr.exp, case_instr.cases)
    assert value_cond is None
    # let vid = value_cond.note.vid in
    # let ctx =
    #   match phantom_opt with
    #   | Some (pid, _) -> Ctx.cover ctx (Option.is_none instrs_opt) pid vid
    #   | None -> ctx
    # in
    # match instrs_opt with
    # | Some instrs -> eval_instrs ctx Cont instrs
    if instrs_opt is not None:
        return eval_instrs(ctx, Cont(), instrs_opt)
    # | None -> (ctx, Cont)
    return ctx, Cont()

def eval_let_instr(ctx, let_instr):
    # let ctx = eval_let_iter ctx exp_l exp_r iterexps in
    # (ctx, Cont)
    ctx = eval_let_iter(ctx, let_instr)
    return ctx, Cont()

def eval_let_list(ctx, exp_l, exp_r, vars_h, iterexps_t):
    # (* Discriminate between bound and binding variables *)
    # let vars_bound, vars_binding =
    #   List.partition
    #     (fun (id, _typ, iters) ->
    #       Ctx.bound_value Local ctx (id, iters @ [ Il.Ast.List ]))
    #     vars
    # in
    vars_bound = []
    vars_binding = []
    for var in vars_h:
        if ctx.bound_value_local(var.id, var.iter + [p4specast.List()]):
            vars_bound.append(var)
        else:
            vars_binding.append(var)
    # (* Create a subcontext for each batch of bound values *)
    # let ctxs_sub = Ctx.sub_list ctx vars_bound in
    ctxs_sub = ctx.sub_list(vars_bound)
    # let ctx, values_binding =
    #   match ctxs_sub with
    #   (* If the bound variable supposed to guide the iteration is already empty,
    #      then the binding variables are also empty *)
    #   | [] ->
    if ctxs_sub == []:
    #       let values_binding =
    #         List.init (List.length vars_binding) (fun _ -> [])
    #       in
    #       (ctx, values_binding)
        values_binding = [[] for _ in vars_binding]
    #   (* Otherwise, evaluate the premise for each batch of bound values,
    #      and collect the resulting binding batches *)
    #   | _ ->
    else:
    #       let ctx, values_binding_batch =
    #         List.fold_left
    #           (fun (ctx, values_binding_batch) ctx_sub ->
    #             let ctx_sub = eval_let_iter' ctx_sub exp_l exp_r iterexps in
    #             let ctx = Ctx.commit ctx ctx_sub in
    #             let value_binding_batch =
    #               List.map
    #                 (fun (id_binding, _typ_binding, iters_binding) ->
    #                   Ctx.find_value Local ctx_sub (id_binding, iters_binding))
    #                 vars_binding
    #             in
    #             let values_binding_batch =
    #               values_binding_batch @ [ value_binding_batch ]
    #             in
    #             (ctx, values_binding_batch))
    #           (ctx, []) ctxs_sub
    #       in
        values_binding_batch = []
        for ctx_sub in ctxs_sub:
            ctx_sub = eval_let_iter_tick(ctx_sub, exp_l, exp_r, iterexps_t)
            ctx = ctx.commit(ctx_sub)
            value_binding_batch = []
            for var_binding in vars_binding:
                value_binding = ctx_sub.find_value_local(var_binding.id, var_binding.iter)
                value_binding_batch.append(value_binding)
            values_binding_batch.append(value_binding_batch)
    #       let values_binding = values_binding_batch |> Ctx.transpose in
        values_binding = context.transpose(values_binding_batch)
        assert len(values_binding) == len(vars_binding)
    #       (ctx, values_binding)
    # in
    # (* Finally, bind the resulting binding batches *)
    # List.fold_left2
    #   (fun ctx (id_binding, typ_binding, iters_binding) values_binding ->
    #     let value_binding =
    #       let vid = Value.fresh () in
    #       let typ = Typ.iterate typ_binding (iters_binding @ [ Il.Ast.List ]) in
    #       Il.Ast.(ListV values_binding $$$ { vid; typ = typ.it })
    #     in
    #     Ctx.add_node ctx value_binding;
    #     List.iter
    #       (fun (id, _typ, iters) ->
    #         let value_sub =
    #           Ctx.find_value Local ctx (id, iters @ [ Il.Ast.List ])
    #         in
    #         Ctx.add_edge ctx value_binding value_sub Dep.Edges.Iter)
    #       vars_bound;
    #     Ctx.add_value Local ctx
    #       (id_binding, iters_binding @ [ Il.Ast.List ])
    #       value_binding)
    for (var_binding, values_binding) in zip(vars_binding, values_binding):
        id_binding = var_binding.id
        typ_binding = var_binding.typ
        iters_binding = var_binding.iter
        value_binding = objects.ListV(values_binding, typ=typ_binding)
        ctx = ctx.add_value_local(id_binding, iters_binding + [p4specast.List()], value_binding)
    return ctx


def eval_let_iter_tick(ctx, exp_l, exp_r, iterexps):
    # INCOMPLETE
    # match iterexps with
    # | [] -> eval_let ctx exp_l exp_r
    if iterexps == []:
        return eval_let(ctx, exp_l, exp_r)
    # | iterexp_h :: iterexps_t -> (
    else:
        iterexp = iterexps[0]
        iterexps_t = iterexps[1:]
        iter_h = iterexp.iter
        vars_h = iterexp.vars
    #     let iter_h, vars_h = iterexp_h in
    #     match iter_h with
    #     | Opt -> eval_let_opt ctx exp_l exp_r vars_h iterexps_t
        if isinstance(iter_h, p4specast.Opt):
            return eval_let_opt(ctx, exp_l, exp_r, vars_h, iterexps_t)
    #     | List -> eval_let_list ctx exp_l exp_r vars_h iterexps_t)
        elif isinstance(iter_h, p4specast.List):
            return eval_let_list(ctx, exp_l, exp_r, vars_h, iterexps_t)
        else:
            assert 0, 'should be unreachable'
    import pdb;pdb.set_trace()
    assert 0, "todo eval_let_iter_tick"

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

def split_exps_without_idx(inputs, exps):
    assert sorted(inputs) == inputs # inputs is sorted
    exps_input = []
    exps_output = []
    for index, exp in enumerate(exps):
        if index in inputs:
            exps_input.append(exp)
        else:
            exps_output.append(exp)
    return exps_input, exps_output

# and eval_rule (ctx : Ctx.t) (id : id) (notexp : notexp) : Ctx.t =
def eval_rule(ctx, id, notexp):
    #   let rel = Ctx.find_rel Local ctx id in
    rel = ctx.find_rel_local(id)
    #   let exps_input, exps_output =
    #     let inputs, _, _ = rel in
    #     let _, exps = notexp in
    #     Hint.split_exps_without_idx inputs exps
    inputs = rel.inputs
    _, exps = notexp.mixop, notexp.exps
    exps_input, exps_output = split_exps_without_idx(inputs, exps)
    #   let ctx, values_input = eval_exps ctx exps_input in
    ctx, values_input = eval_exps(ctx, exps_input)
    #   let ctx, values_output =
    #     match invoke_rel ctx id values_input with
    #     | Some (ctx, values_output) -> (ctx, values_output)
    #     | None -> error id.at "relation was not matched"
    relctx, values_output = invoke_rel(ctx, id, values_input)
    if relctx is None:
        raise ValueError("relation was not matched: %s" % id.value)
    ctx = relctx
    #   assign_exps ctx exps_output values_output
    ctx = assign_exps(ctx, exps_output, values_output)
    return ctx


def eval_rule_iter_tick(ctx, id, notexp, iterexps):
    # match iterexps with
    #   match iterexps with
    #   | [] -> eval_rule ctx id notexp
    if not iterexps:
        return eval_rule(ctx, id, notexp)
    assert 0, "TODO eval_rule_iter_tick"
    #   | iterexp_h :: iterexps_t -> (
    #       let iter_h, vars_h = iterexp_h in
    #       match iter_h with
    #       | Opt -> eval_rule_opt ctx id notexp vars_h iterexps_t
    #       | List -> eval_rule_list ctx id notexp vars_h iterexps_t)
    iter_h, vars_h = iterexps[0]
    iterexps_t = iterexps[1:]
    if iter_h == 'Opt':
        return eval_rule_opt(ctx, id, notexp, vars_h, iterexps_t)
    elif iter_h == 'List':
        return eval_rule_list(ctx, id, notexp, vars_h, iterexps_t)
    else:
        assert False, "unknown iter_h: %s" % iter_h

def eval_rule_iter(ctx, instr):
    # let iterexps = List.rev iterexps in
    # eval_rule_iter' ctx id notexp iterexps
    iterexps = instr.iters[::-1]
    return eval_rule_iter_tick(ctx, instr.id, instr.notexp, iterexps)

def eval_rule_instr(ctx, instr):
    # let ctx = eval_rule_iter ctx id notexp iterexps in
    ctx = eval_rule_iter(ctx, instr)
    return ctx, Cont()


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
    elif isinstance(exp, p4specast.TupleE) and \
         isinstance(value, objects.TupleV):
        exps_inner = exp.elts
        values_inner = value.elements
        ctx = assign_exps(ctx, exps_inner, values_inner)
        return ctx
    # | CaseE notexp, CaseV (_mixop_value, values_inner) ->
    #     let _mixop_exp, exps_inner = notexp in
    #     let ctx = assign_exps ctx exps_inner values_inner in
    #     List.iter
    #       (fun value_inner -> Ctx.add_edge ctx value_inner value Dep.Edges.Assign)
    #       values_inner;
    #     ctx
    elif isinstance(exp, p4specast.CaseE) and\
         isinstance(value, objects.CaseV):
        notexp = exp.notexp
        mixop_exp, exps_inner = notexp.mixop, notexp.exps
        values_inner = value.values
        ctx = assign_exps(ctx, exps_inner, values_inner)
        # for value_inner in values_inner:
        #    assert False, "ctx.add_edge(ctx, value_inner, value, dep.edges.Assign)"
        return ctx
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
    elif isinstance(exp, p4specast.ConsE) and \
         isinstance(value, objects.ListV):
        values_inner = value.elements
        assert values_inner, "cannot assign empty list to ConsE"
    #     let value_h = List.hd values_inner in
        value_h = values_inner[0]
    #     let value_t =
    #       let vid = Value.fresh () in
    #       let typ = note in
    #       Il.Ast.(ListV (List.tl values_inner) $$$ { vid; typ })
        value_t = objects.ListV(values_inner[1:], typ=value.typ)
    #     in
    #     Ctx.add_node ctx value_t;
    #     let ctx = assign_exp ctx exp_h value_h in
        ctx = assign_exp(ctx, exp.head, value_h)
    #     Ctx.add_edge ctx value_h value Dep.Edges.Assign;
    #     let ctx = assign_exp ctx exp_t value_t in
        ctx = assign_exp(ctx, exp.tail, value_t)
    #     Ctx.add_edge ctx value_t value Dep.Edges.Assign;
    #     ctx
        return ctx
    # | IterE (_, (Opt, vars)), OptV None ->
    elif (isinstance(exp, p4specast.IterE) and 
          isinstance(exp.iter, p4specast.Opt) and
          isinstance(value, objects.OptV)):
        if value.value is None:
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
            for var in exp.varlist:
                value_sub = objects.OptV(None, typ=var.typ)
                ctx = ctx.add_value_local(var.id, var.iter + [p4specast.Opt()], value_sub)
            return ctx
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
    elif (isinstance(exp, p4specast.IterE) and 
          isinstance(exp.iter, p4specast.List) and
          isinstance(value, objects.ListV)):
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
        ctxs = []
        values = value.elements
        for value_elem in values:
            ctx_local = ctx.localize_venv(venv={})
            ctx_local = assign_exp(ctx_local, exp.exp, value_elem)
            ctxs.append(ctx_local)

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

        for var in exp.varlist:
            # collect elementwise values from each ctx in ctxs
            values = [ctx_elem.find_value_local(var.id, var.iter) for ctx_elem in ctxs]
            # create a ListV value for these
            value_sub = objects.ListV(values, typ=var.typ)
            ctx = ctx.add_value_local(var.id, var.iter + [p4specast.List()], value_sub)
        return ctx

    import pdb;pdb.set_trace()
    assert 0, "todo assign_exp"
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
    if isinstance(value, objects.FuncV):
        func = ctx_caller.find_func_local(value.id)
        return ctx_callee.add_func_local(id, func)
    else:
        assert False, "cannot assign a value %s to a definition %s" % (
            str(value), str(id))

def eval_result_instr(ctx, instr):
    # type: (context.Context, p4specast.ResultI) -> tuple[context.Context, Res]
    #  let ctx, values = eval_exps ctx exps in
    #  (ctx, Res values)
    ctx, values = eval_exps(ctx, instr.exps)
    return ctx, Res(values)

def eval_return_instr(ctx, instr):
    # let ctx, value = eval_exp ctx exp in
    # (ctx, Ret value)
    ctx, value = eval_exp(ctx, instr.exp)
    return (ctx, Ret(value))

# ____________________________________________________________
# expressions

def eval_exp(ctx, exp):
    return exp.eval_exp(ctx)

def eval_exps(ctx, exps):
    # List.fold_left
    #   (fun (ctx, values) exp ->
    #     let ctx, value = eval_exp ctx exp in
    #     (ctx, values @ [ value ]))
    #   (ctx, []) exps
    values = []
    for exp in exps:
        ctx, value = eval_exp(ctx, exp)
        values.append(value)
    return ctx, values

class __extend__(p4specast.Exp):
    def eval_exp(self, ctx):
        import pdb;pdb.set_trace()
        raise NotImplementedError("abstract base class %s" % self)

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
        return ctx, objects.BoolV(self.value, typ=self.typ)

class __extend__(p4specast.NumE):
    def eval_exp(self, ctx):
        return ctx, objects.NumV(self.value, self.what, typ=self.typ)

class __extend__(p4specast.TextE):
    def eval_exp(self, ctx):
        return ctx, objects.TextV(self.value, typ=self.typ)

class __extend__(p4specast.VarE):
    def eval_exp(self, ctx):
        # let value = Ctx.find_value Local ctx (id, []) in
        value = ctx.find_value_local(self.id, [])
        return ctx, value

class __extend__(p4specast.OptE):
    def eval_exp(self, ctx):
        #     Ctx.t * value =
        #   let ctx, value_opt =
        #     match exp_opt with
        if self.exp is not None:
            ctx, value = eval_exp(ctx, self.exp)
        else:
            value = None
        #     | Some exp ->
        #         let ctx, value = eval_exp ctx exp in
        #         (ctx, Some value)
        #     | None -> (ctx, None)
        #   in
        #   let value_res =
        #     let vid = Value.fresh () in
        #     let typ = note in
        #     Il.Ast.(OptV value_opt $$$ { vid; typ })
        value_res = objects.OptV(value, typ=self.typ)
        return ctx, value_res
        #   in
        #   Ctx.add_node ctx value_res;
        #   if Option.is_none value_opt then
        #     List.iter
        #       (fun value_input ->
        #         Ctx.add_edge ctx value_res value_input Dep.Edges.Control)
        #       ctx.local.values_input;
        #   (ctx, value_res)

class __extend__(p4specast.TupleE):
    def eval_exp(self, ctx):
        #   let ctx, values = eval_exps ctx exps in
        ctx, values = eval_exps(ctx, self.elts)
        #   let value_res =
        #     let vid = Value.fresh () in
        #     let typ = note in
        #     Il.Ast.(TupleV values $$$ { vid; typ })
        value_res = objects.TupleV(values, typ=self.typ)
        #   in
        #   Ctx.add_node ctx value_res;
        #   if List.length values = 0 then
        #     List.iter
        #       (fun value_input ->
        #         Ctx.add_edge ctx value_res value_input Dep.Edges.Control)
        #       ctx.local.values_input;
        #   (ctx, value_res)
        return ctx, value_res

class __extend__(p4specast.ListE):
    def eval_exp(self, ctx):
        #   let ctx, values = eval_exps ctx exps in
        ctx, values = eval_exps(ctx, self.elts)
        #   let value_res =
        #     let vid = Value.fresh () in
        #     let typ = note in
        #     Il.Ast.(ListV values $$$ { vid; typ })
        value_res = objects.ListV(values, typ=self.typ)
        #   in
        #   Ctx.add_node ctx value_res;
        #   if List.length values = 0 then
        #     List.iter
        #       (fun value_input ->
        #         Ctx.add_edge ctx value_res value_input Dep.Edges.Control)
        #       ctx.local.values_input;        
        #   (ctx, value_res)
        return ctx, value_res

def eval_cmp_bool(cmpop, value_l, value_r, typ):
    # let eq = Value.eq value_l value_r in
    eq = value_l.eq(value_r)
    # match cmpop with `EqOp -> Il.Ast.BoolV eq | `NeOp -> Il.Ast.BoolV (not eq)
    value = eq if cmpop == 'EqOp' else not eq
    return objects.BoolV(value, typ=typ)


def eval_cmp_num(cmpop, value_l, value_r, typ):
    # let num_l = Value.get_num value_l in
    assert value_l.what == value_r.what
    num_l = value_l.get_num()
    # let num_r = Value.get_num value_r in
    num_r = value_r.get_num()
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
    return objects.BoolV(res, typ=typ)
    # Il.Ast.BoolV (Num.cmp cmpop num_l num_r)


class __extend__(p4specast.CmpE):
    def eval_exp(self, ctx):
        # let ctx, value_l = eval_exp ctx exp_l in
        ctx, value_l = eval_exp(ctx, self.left)
        # let ctx, value_r = eval_exp ctx exp_r in
        ctx, value_r = eval_exp(ctx, self.right)
        # let value_res =
        #   match cmpop with
        #   | #Bool.cmpop as cmpop -> eval_cmp_bool cmpop value_l value_r
        if self.cmpop in ('EqOp', 'NeOp'):
            value_res = eval_cmp_bool(self.cmpop, value_l, value_r, self.typ)
        #   | #Num.cmpop as cmpop -> eval_cmp_num cmpop value_l value_r
        elif self.cmpop in ('LtOp', 'GtOp', 'LeOp', 'GeOp'):
            value_res = eval_cmp_num(self.cmpop, value_l, value_r, self.typ)
        else:
            assert 0, 'should be unreachable'
        # in
        # let value_res =
        #   let vid = Value.fresh () in
        #   let typ = note in
        #   Il.Ast.(value_res $$$ { vid; typ })
        # in
        # Ctx.add_node ctx value_res;
        # Ctx.add_edge ctx value_res value_l (Dep.Edges.Op (CmpOp cmpop));
        # Ctx.add_edge ctx value_res value_r (Dep.Edges.Op (CmpOp cmpop));
        # (ctx, value_res)
        return ctx, value_res

def eval_binop_bool(binop, value_l, value_r, typ):
    # let bool_l = Value.get_bool value_l in
    bool_l = value_l.get_bool()
    # let bool_r = Value.get_bool value_r in
    bool_r = value_r.get_bool()
    # match binop with
    # | `AndOp -> Il.Ast.BoolV (bool_l && bool_r)
    if binop == 'AndOp':
        res_bool = objects.BoolV(bool_l and bool_r)
    # | `OrOp -> Il.Ast.BoolV (bool_l || bool_r)
    elif binop == 'OrOp':
        res_bool = objects.BoolV(bool_l or bool_r)
    # | `ImplOp -> Il.Ast.BoolV ((not bool_l) || bool_r)
    elif binop == 'ImplOp':
        res_bool = objects.BoolV((not bool_l) or bool_r)
    # | `EquivOp -> Il.Ast.BoolV (bool_l = bool_r)
    elif binop == 'EquivOp':
        res_bool = objects.BoolV(bool_l == bool_r)
    else:
        assert 0, "should be unreachable"
    return objects.BoolV(res_bool, typ=typ)

def eval_binop_num(binop, value_l, value_r, typ):
    # let num_l = Value.get_num value_l in
    # let num_r = Value.get_num value_r in
    # Il.Ast.NumV (Num.bin binop num_l num_r)
    assert value_l.what == value_r.what
    num_l = value_l.get_num()
    num_r = value_r.get_num()
    if binop == 'AddOp':
        res_num = num_l.add(num_r)
    elif binop == 'SubOp':
        res_num = num_l.sub(num_r)
    elif binop == 'MulOp':
        res_num = num_l.mul(num_r)
    elif binop == 'DivOp':
        raise NotImplementedError("DivOp")
    elif binop == 'ModOp':
        raise NotImplementedError("ModOp")
    elif binop == 'PowOp':
        raise NotImplementedError("PowOp")
    else:
        assert 0, "should be unreachable"
    return objects.NumV(res_num, value_l.what, typ=typ)

class __extend__(p4specast.BinE):
    def eval_exp(self, ctx):
        # let ctx, value_l = eval_exp ctx exp_l in
        ctx, value_l = eval_exp(ctx, self.left)
        # let ctx, value_r = eval_exp ctx exp_r in
        ctx, value_r = eval_exp(ctx, self.right)
        # let value_res =
        #   match binop with
        #   | #Bool.binop as binop -> eval_bin_bool binop value_l value_r
        if self.binop in ('AndOp', 'OrOp', 'ImplOp', 'EquivOp'):
            value_res = eval_binop_bool(self.binop, value_l, value_r, self.typ)
        #   | #Num.binop as binop -> eval_bin_num binop value_l value_r
        elif self.binop in ('AddOp', 'SubOp', 'MulOp', 'DivOp', 'ModOp', 'PowOp'):
            value_res = eval_binop_num(self.binop, value_l, value_r, self.typ)
        else:
            assert 0, "should be unreachable"
        # in
        # let value_res =
        #   let vid = Value.fresh () in
        #   let typ = note in
        #   Il.Ast.(value_res $$$ { vid; typ })
        # in
        # Ctx.add_node ctx value_res;
        # Ctx.add_edge ctx value_res value_l (Dep.Edges.Op (BinOp binop));
        # Ctx.add_edge ctx value_res value_r (Dep.Edges.Op (BinOp binop));
        # (ctx, value_res)
        return ctx, value_res

def eval_unop_bool(unop, value, typ):
    # match unop with `NotOp -> Il.Ast.BoolV (not (Value.get_bool value))
    if unop == 'NotOp':
        return objects.BoolV(not value.get_bool(), typ=typ)
    else:
        assert 0, "Unknown boolean unary operator: %s" % unop

def eval_unop_num(unop, value, typ):
    # let num = Value.get_num value in
    num = value.get_num()
    # match unop with
    if unop == 'PlusOp':
        return objects.NumV(num, value.what, typ=typ)
    elif unop == 'MinusOp':
        return objects.NumV(num.neg(), value.what, typ=typ)
    else:
        assert 0, "Unknown numeric unary operator: %s" % unop

class __extend__(p4specast.UnE):
    def eval_exp(self, ctx):
        # let ctx, value = eval_exp ctx exp in
        ctx, value = eval_exp(ctx, self.exp)
        unop = self.op
        if unop in ('NotOp',):
            value_res = eval_unop_bool(unop, value, self.typ)
        elif unop in ('PlusOp', 'MinusOp'):
            value_res = eval_unop_num(unop, value, self.typ)
        else:
            assert 0, "Unknown unary operator: %s" % unop
        return ctx, value_res

class __extend__(p4specast.MemE):
    def eval_exp(self, ctx):
        #   let ctx, value_e = eval_exp ctx exp_e in
        ctx, value_e = eval_exp(ctx, self.elem)
        #   let ctx, value_s = eval_exp ctx exp_s in
        ctx, value_s = eval_exp(ctx, self.lst)
        #   let values_s = Value.get_list value_s in
        values_s = value_s.get_list()
        #   let value_res =
        #     let vid = Value.fresh () in
        #     let typ = note in
        #     Il.Ast.(BoolV (List.exists (Value.eq value_e) values_s) $$$ { vid; typ })
        res = False
        for v in values_s:
            if value_e.eq(v):
                res = True
                break
        value_res = objects.BoolV(res, typ=self.typ)
        return ctx, value_res
        #   in
        #   Ctx.add_node ctx value_res;
        #   Ctx.add_edge ctx value_res value_e (Dep.Edges.Op MemOp);
        #   Ctx.add_edge ctx value_res value_s (Dep.Edges.Op MemOp);
        #   (ctx, value_res)

class __extend__(p4specast.DotE):
    def eval_exp(self, ctx):
        #   let ctx, value_b = eval_exp ctx exp_b in
        ctx, value_b = eval_exp(ctx, self.obj)
        #   let fields = Value.get_struct value_b in
        fields = value_b.get_struct()
        for (atom, value) in fields:
            if atom.value == self.field.value:
                return ctx, value
        assert 0, "field not found"
        #   let value_res =
        #     fields
        #     |> List.map (fun (atom, value) -> (atom.it, value))
        #     |> List.assoc atom.it
        #   in
        #   (ctx, value_res)

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
        value_res = objects.BoolV(sub, typ=note)
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

class __extend__(p4specast.UpCastE):
    def eval_exp(self, ctx):
        # let ctx, value = eval_exp ctx exp in
        ctx, value = eval_exp(ctx, self.exp)
        # let ctx, value_res = upcast ctx typ value in
        # (ctx, value_res)
        return upcast(ctx, self.check_typ, value)

class __extend__(p4specast.MatchE):
    def eval_exp(self, ctx):
        # INCOMPLETE
        # let ctx, value = eval_exp ctx exp in
        ctx, value = eval_exp(ctx, self.exp)
        # let matches =
        #   match (pattern, value.it) with
        pattern = self.pattern
        #   | CaseP mixop_p, CaseV (mixop_v, _) -> Mixop.eq mixop_p mixop_v
        if (isinstance(pattern, p4specast.CaseP) and
                isinstance(value, objects.CaseV)):
            matches = mixop_eq(pattern.mixop, value.mixop)
        #   | ListP listpattern, ListV values -> (
        elif (isinstance(pattern, p4specast.ListP) and
                isinstance(value, objects.ListV)):
            listpattern = pattern.element
            len_v = len(value.elements)
        #       let len_v = List.length values in
        #       match listpattern with
        #       | `Cons -> len_v > 0
            if isinstance(listpattern, p4specast.Cons):
                matches = (len_v > 0)
        #       | `Fixed len_p -> len_v = len_p
            elif isinstance(listpattern, p4specast.Fixed):
                matches = (len_v == listpattern.length)
        #       | `Nil -> len_v = 0)
            elif isinstance(listpattern, p4specast.Nil):
                matches = (len_v == 0)
            else:
                assert 0, "should be unreachable"
        #   | OptP `Some, OptV (Some _) -> true
        #   | OptP `None, OptV None -> true
        elif (isinstance(pattern, p4specast.OptP) and
              isinstance(value, objects.OptV)):
            assert pattern.kind in ('Some', 'None')
            matches = (value.value is None) == (pattern.kind == 'None')
        #   | _ -> false
        else:
            import pdb;pdb.set_trace()
            assert 0, "TODO MatchE"
        # in
        # let value_res =
        #   let vid = Value.fresh () in
        #   let typ = note in
        #   Il.Ast.(BoolV matches $$$ { vid; typ })
        value_res = objects.BoolV(matches, typ=self.typ)
        # in
        # Ctx.add_node ctx value_res;
        # Ctx.add_edge ctx value_res value (Dep.Edges.Op (MatchOp pattern));
        # (ctx, value_res)
        return ctx, value_res

class __extend__(p4specast.CallE):
    def eval_exp(self, ctx):
        # let ctx, value_res = invoke_func ctx id targs args in
        # (ctx, value_res)
        return invoke_func(ctx, self)

class __extend__(p4specast.HoldE):
    def eval_exp(self, ctx):
        # let _, exps_input = notexp in
        exps_input = self.notexp.exps
        # let ctx, values_input = eval_exps ctx exps_input in
        ctx, values_input = eval_exps(ctx, exps_input)
        # let ctx, hold =
        #   match invoke_rel ctx id values_input with
        #   | Some (ctx, _) -> (ctx, true)
        #   | None -> (ctx, false)
        relctx, _ = invoke_rel(ctx, self.id, values_input)
        if relctx is not None:
            ctx = relctx
            hold = True
        else:
            hold = False
        # in
        # let value_res =
        #   let vid = Value.fresh () in
        #   let typ = note in
        #   Il.Ast.(BoolV hold $$$ { vid; typ })
        value_res = objects.BoolV(hold, typ=self.typ)
        # in
        # Ctx.add_node ctx value_res;
        # List.iteri
        #   (fun idx value_input ->
        #     Ctx.add_edge ctx value_res value_input (Dep.Edges.Rel (id, idx)))
        #   values_input;
        # (ctx, value_res)
        return ctx, value_res

class __extend__(p4specast.StrE):
    def eval_exp(self, ctx):
        # let atoms, exps = List.split fields in
        exps = [exp for (atom, exp) in self.fields]
        # let ctx, values = eval_exps ctx exps in
        ctx, values = eval_exps(ctx, exps)
        # let fields = List.combine atoms values in
        fields = [(atom, value) for ((atom, exp), value) in zip(self.fields, values)]
        # let value_res =
        #   let vid = Value.fresh () in
        #   let typ = note in
        #   Il.Ast.(StructV fields $$$ { vid; typ })
        # in
        value_res = objects.StructV(fields, typ=self.typ)
        # Ctx.add_node ctx value_res;
        # if List.length values = 0 then
        #   List.iter
        #     (fun value_input ->
        #       Ctx.add_edge ctx value_res value_input Dep.Edges.Control)
        #     ctx.local.values_input;
        # (ctx, value_res)
        return ctx, value_res

class __extend__(p4specast.CaseE):
    def eval_exp(self, ctx):
        # let mixop, exps = notexp in
        mixop = self.notexp.mixop
        exps = self.notexp.exps
        # let ctx, values = eval_exps ctx exps in
        ctx, values = eval_exps(ctx, exps)
        # let value_res =
        #   let vid = Value.fresh () in
        #   let typ = note in
        #   Il.Ast.(CaseV (mixop, values) $$$ { vid; typ })
        value_res = objects.CaseV(mixop, values, typ=self.typ)
        # in
        # Ctx.add_node ctx value_res;
        # if List.length values = 0 then
        #   List.iter
        #     (fun value_input ->
        #       Ctx.add_edge ctx value_res value_input Dep.Edges.Control)
        #     ctx.local.values_input;
        # (ctx, value_res)
        return ctx, value_res

class __extend__(p4specast.CatE):
    def eval_exp(self, ctx):
        #   let ctx, value_l = eval_exp ctx exp_l in
        ctx, value_l = eval_exp(ctx, self.left)
        #   let ctx, value_r = eval_exp ctx exp_r in
        ctx, value_r = eval_exp(ctx, self.right)
        #   let value_res =
        #     match (value_l.it, value_r.it) with
        #     | TextV s_l, TextV s_r -> Il.Ast.TextV (s_l ^ s_r)
        if isinstance(value_l, objects.TextV) and isinstance(value_r, objects.TextV):
            value_res = objects.TextV(value_l.value + value_r.value, typ=self.typ)
        #     | ListV values_l, ListV values_r -> Il.Ast.ListV (values_l @ values_r)
        else:
            import pdb;pdb.Set_trace()
            assert 0, "TODO CatE"
        #     | _ -> error at "concatenation expects either two texts or two lists"
        #   in
        #   let value_res =
        #     let vid = Value.fresh () in
        #     let typ = note in
        #     Il.Ast.(value_res $$$ { vid; typ })
        #   in
        #   Ctx.add_node ctx value_res;
        #   Ctx.add_edge ctx value_res value_l (Dep.Edges.Op CatOp);
        #   Ctx.add_edge ctx value_res value_r (Dep.Edges.Op CatOp);
        #   (ctx, value_res)
        return ctx, value_res

class __extend__(p4specast.ConsE):
    def eval_exp(self, ctx):
        # let ctx, value_h = eval_exp ctx exp_h in
        ctx, value_h = eval_exp(ctx, self.head)
        # let ctx, value_t = eval_exp ctx exp_t in
        ctx, value_t = eval_exp(ctx, self.tail)
        # let values_t = Value.get_list value_t in
        values_t = value_t.get_list()
        # let value_res =
        #   let vid = Value.fresh () in
        #   let typ = note in
        #   Il.Ast.(ListV (value_h :: values_t) $$$ { vid; typ })
        value_res = objects.ListV([value_h] + values_t, typ=self.typ)
        return ctx, value_res
        # in
        # Ctx.add_node ctx value_res;
        # (ctx, value_res)

class __extend__(p4specast.LenE):
    def eval_exp(self, ctx):
        # let ctx, value = eval_exp ctx exp in
        ctx, value = eval_exp(ctx, self.lst)
        # let len = value |> Value.get_list |> List.length |> Bigint.of_int in
        value = integers.Integer.fromint(len(value.get_list()))
        # let value_res =
        #   let vid = Value.fresh () in
        #   let typ = note in
        #   Il.Ast.(NumV (`Nat len) $$$ { vid; typ })
        value_res = objects.NumV(value, 'Nat', typ=self.typ)
        # in
        # Ctx.add_node ctx value_res;
        # Ctx.add_edge ctx value_res value (Dep.Edges.Op LenOp);
        # (ctx, value_res)
        return ctx, value_res


def eval_iter_exp_opt(note, ctx, exp, vars):
    #   let ctx_sub_opt = Ctx.sub_opt ctx vars in
    ctx_sub_opt = ctx.sub_opt(vars)
    #   let ctx, value_res =
    #     match ctx_sub_opt with
    #     | Some ctx_sub ->
    if ctx_sub_opt is not None:
        import pdb;pdb.set_trace()
        ctx_sub = ctx_sub_opt
    #         let ctx_sub, value = eval_exp ctx_sub exp in
        ctx_sub, value = eval_exp(ctx_sub, exp)
    #         let ctx = Ctx.commit ctx ctx_sub in
        ctx = ctx.commit(ctx_sub)
    #         let value_res =
    #           let vid = Value.fresh () in
    #           let typ = note in
    #           Il.Ast.(OptV (Some value) $$$ { vid; typ })
    #         in
    #         (ctx, value_res)
        value_res = objects.OptV(value, typ=note)
        return ctx, value_res
    #     | None ->
    else:
    #         let value_res =
    #           let vid = Value.fresh () in
    #           let typ = note in
    #           Il.Ast.(OptV None $$$ { vid; typ })
        value_res = objects.OptV(None, typ=note)
    #         in
    #         (ctx, value_res)
        return ctx, value_res
    #   in
    #   Ctx.add_node ctx value_res;
    #   List.iter
    #     (fun (id, _typ, iters) ->
    #       let value_sub = Ctx.find_value Local ctx (id, iters @ [ Il.Ast.Opt ]) in
    #       Ctx.add_edge ctx value_res value_sub Dep.Edges.Iter)
    #     vars;
    #   (ctx, value_res)


def eval_iter_exp_list(note, ctx, exp, vars):
    # let ctxs_sub = Ctx.sub_list ctx vars in
    ctxs_sub = ctx.sub_list(vars)
    # let ctx, values =
    values = []
    for ctx_sub in ctxs_sub:
        #   List.fold_left
        #     (fun (ctx, values) ctx_sub ->
        #       let ctx_sub, value = eval_exp ctx_sub exp in
        ctx_sub, value = eval_exp(ctx_sub, exp)
        #       let ctx = Ctx.commit ctx ctx_sub in
        ctx = ctx.commit(ctx_sub)
        #       (ctx, values @ [ value ]))
        #     (ctx, []) ctxs_sub
        values.append(value)
    # in
    # let value_res =
    #   let vid = Value.fresh () in
    #   let typ = note in
    #   Il.Ast.(ListV values $$$ { vid; typ })
    # in
    value_res = objects.ListV(values, typ=note)
    # Ctx.add_node ctx value_res;
    # List.iter
    #   (fun (id, _typ, iters) ->
    #     let value_sub = Ctx.find_value Local ctx (id, iters @ [ Il.Ast.List ]) in
    #     Ctx.add_edge ctx value_res value_sub Dep.Edges.Iter)
    #   vars;
    # (ctx, value_res)
    return ctx, value_res

class __extend__(p4specast.IterE):
    def eval_exp(self, ctx):
        # let iter, vars = iterexp in
        # match iter with
        if isinstance(self.iter, p4specast.Opt):
            # | Opt -> eval_iter_exp_opt note ctx exp vars
            return eval_iter_exp_opt(self.typ, ctx, self.exp, self.varlist)
        if isinstance(self.iter, p4specast.List):
            # | List -> eval_iter_exp_list note ctx exp vars
            return eval_iter_exp_list(self.typ, ctx, self.exp, self.varlist)
        else:
            assert False, "Unknown iter kind: %s" % iter

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
            assert 0, "TODO subtyp"
    #     match (deftyp.it, value.it) with
    #     | PlainT typ, _ ->
    #         let typ = Typ.subst_typ theta typ in
    #         subtyp ctx typ value
    #     | VariantT typcases, CaseV (mixop_v, _) ->
        if (isinstance(deftyp, p4specast.VariantT) and
                isinstance(value, objects.CaseV)):
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
    assert 0, "TODO subtyp"

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
        assert 0, "TODO downcast"
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
            assert 0, "TODO downcast"
    #         let typ = Typ.subst_typ theta typ in
    #         downcast ctx typ value
    #     | _ -> (ctx, value))
        else:
            return ctx, value
    # | TupleT typs -> (
    if isinstance(typ, p4specast.TupleT):
        import pdb;pdb.set_trace()
        assert 0, "TODO downcast"
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

def upcast(ctx, typ, value):
    # INCOMPLETE
    #   match typ.it with
    #   | NumT `IntT -> (
    if isinstance(typ, p4specast.NumT) and isinstance(typ.typ, p4specast.IntT):
    #       match value.it with
        assert value.what == 'Nat'
    #       | NumV (`Nat n) ->
    #           let value_res =
    #             let vid = Value.fresh () in
    #             let typ = typ.it in
    #             Il.Ast.(NumV (`Int n) $$$ { vid; typ })
        value_res = objects.NumV(value.get_num(), 'Int', typ=typ)
        return ctx, value_res
    #           in
    #           Ctx.add_node ctx value_res;
    #           Ctx.add_edge ctx value_res value (Dep.Edges.Op (CastOp typ));
    #           (ctx, value_res)
    #       | NumV (`Int _) -> (ctx, value)
    #       | _ -> assert false)
    #   | VarT (tid, targs) -> (
    if isinstance(typ, p4specast.VarT):
        tparams, deftyp = ctx.find_typdef_local(typ.id)
        assert tparams == [] # TODO
    #       let tparams, deftyp = Ctx.find_typdef Local ctx tid in
    #       let theta = List.combine tparams targs |> TIdMap.of_list in
    #       match deftyp.it with
        if isinstance(deftyp, p4specast.PlainT):
            import pdb;pdb.set_trace()
            assert 0, "TODO upcast"
        else:
            return ctx, value
    import pdb;pdb.set_trace()
    assert 0, "TODO upcast"
    #       | PlainT typ ->
    #           let typ = Typ.subst_typ theta typ in
    #           upcast ctx typ value
    #       | _ -> (ctx, value))
    #   | TupleT typs -> (
    #       match value.it with
    #       | TupleV values ->
    #           let ctx, values =
    #             List.fold_left2
    #               (fun (ctx, values) typ value ->
    #                 let ctx, value = upcast ctx typ value in
    #                 (ctx, values @ [ value ]))
    #               (ctx, []) typs values
    #           in
    #           let value_res =
    #             let vid = Value.fresh () in
    #             let typ = typ.it in
    #             Il.Ast.(TupleV values $$$ { vid; typ })
    #           in
    #           Ctx.add_node ctx value_res;
    #           Ctx.add_edge ctx value_res value (Dep.Edges.Op (CastOp typ));
    #           (ctx, value_res)
    #       | _ -> assert false)
    #   | _ -> (ctx, value)


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
