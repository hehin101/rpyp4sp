from __future__ import print_function
from rpython.rlib import objectmodel, jit
from rpyp4sp import p4specast, objects, builtin, context, integers
from rpyp4sp.error import (P4Error, P4EvaluationError, P4CastError,
                           P4NotImplementedError, P4RelationError)
from rpyp4sp.sign import Res, Ret

class VarList(object):
    _immutable_fields_ = ['vars[*]']

    def __init__(self, vars):
        self.vars = vars  # type: list
        self.next_var_lists = {}  # type: dict[tuple[str, str], VarList]
        self._ctx_env_key_cache = None
        self._ctx_env_key_result = None

    @jit.elidable
    def add_var(self, var):
        # type: (object) -> VarList
        key = (var.id.value, var.iter.to_key())
        res = self.next_var_lists.get(key)
        if res is not None:
            return res
        else:
            new_vars = self.vars + [var]
            res = VarList(new_vars)
            self.next_var_lists[key] = res
            return res

    def tostring(self):
        if not self.vars:
            return "[]"
        return "[%s]" % ", ".join([var.tostring() for var in self.vars])

    def __repr__(self):
        l = ["interp.VARLIST_ROOT"]
        for var in self.vars:
            l.append(".add_var(%r)" % var)
        return "".join(l)

VARLIST_ROOT = VarList([])

def invoke_func(ctx, calle):
    try:
        return _invoke_func(ctx, calle)
    except P4Error as e:
        e.traceback_add_frame('???', calle.region, calle)
        raise

def _invoke_func(ctx, calle):
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

def get_printable_location(func):
    return func.id.value

invoke_func_def_jit_driver = jit.JitDriver(
    reds='auto', greens=['func'],
    should_unroll_one_iteration = lambda func: True,
    name='invoke_func', get_printable_location=get_printable_location,
    is_recursive=True)

@jit.unroll_safe
def invoke_func_def(ctx, calle):
    from rpyp4sp.type_helpers import subst_typ_ctx
    # let tparams, args_input, instrs = Ctx.find_func Local ctx id in
    func = ctx.find_func_local(calle.func, calle)
    # check (instrs <> []) id.at "function has no instructions";
    assert func.instrs
    # let ctx_local = Ctx.localize ctx in
    ctx_local = ctx.localize()
    # check
    #   (List.length targs = List.length tparams)
    #   id.at "arity mismatch in type arguments";
    assert len(calle.targs) == len(func.tparams), "arity mismatch in type arguments"
    if calle.targs:
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
        targs = [subst_typ_ctx(ctx, targ) for targ in calle.targs]
    # in
    # let ctx_local =
    #   List.fold_left2
    #     (fun ctx_local tparam targ ->
    #       Ctx.add_typdef Local ctx_local tparam ([], Il.Ast.PlainT targ $ targ.at))
    #     ctx_local tparams targs
    # in
    # let ctx, values_input = eval_args ctx args in
        for i, tparam in enumerate(func.tparams):
            targ = targs[i]
            ctx_local = ctx_local.add_typdef_local(tparam, ([], p4specast.PlainT(targ)))
    ctx, values_input = eval_args(ctx, calle.args)
    try:
        return invoke_func_def_attempt_clauses(ctx, func, values_input, ctx_local=ctx_local)
    except P4Error as e:
        e.traceback_patch_last_name(func.id.value)
        raise

def invoke_func_def_attempt_clauses(ctx, func, values_input, ctx_local=None):
    # INCOMPLETE
    # and invoke_func_def (ctx : Ctx.t) (id : id) (targs : targ list) (args : arg list) : Ctx.t * value =
    # let tparams, args_input, instrs = Ctx.find_func Local ctx id in
    tparams, args_input, instrs = func.tparams, func.args, func.instrs
    # let ctx_local = Ctx.localize ctx in
    if ctx_local is None:
        ctx_local = ctx.localize()
    # let ctx_local = Ctx.localize_inputs ctx_local values_input in
    # let ctx_local = assign_args ctx ctx_local args_input values_input in
    ctx_local = assign_args(ctx, ctx_local, func, values_input)
    sign = _func_eval_instrs(ctx_local, func)
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
    raise P4EvaluationError("function was not matched: %s" % (func.id.value))

def _func_eval_instrs(ctx_local, func):
    invoke_func_def_jit_driver.jit_merge_point(func=func)
    # let ctx_local, sign = eval_instrs ctx_local Cont instrs in
    return eval_instrs(ctx_local, func.instrs)

def eval_arg(ctx, arg):
    # match arg.it with
    # | ExpA exp -> eval_exp ctx exp
    if isinstance(arg, p4specast.ExpA):
        return eval_exp(ctx, arg.exp)
    # | DefA id ->
    #     let value_res =
    #       let vid = Value.fresh () in
    #       let typ = Il.Ast.FuncT in
    #       Il.Ast.(FuncV id $$$ { vid; typ })
    #     in
    #     Ctx.add_node ctx value_res;
    #     (ctx, value_res)
    elif isinstance(arg, p4specast.DefA):
        return ctx, objects.FuncV(arg.id, p4specast.FuncT.INSTANCE)
    else:
        assert 0, "unreachable"

@jit.unroll_safe
def eval_args(ctx, args):
    # List.fold_left
    #   (fun (ctx, values) arg ->
    #     let ctx, value = eval_arg ctx arg in
    #     (ctx, values @ [ value ]))
    #   (ctx, []) args
    values = [None] * len(args)
    for i, arg in enumerate(args):
        ctx, value = eval_arg(ctx, arg)
        values[i] = value
    return ctx, values

# ____________________________________________________________
# relations

def get_printable_location(reld):
    return reld.id.value

invoke_rel_jit_driver = jit.JitDriver(
    reds='auto', greens=['reld'],
    should_unroll_one_iteration = lambda reld: True,
    name='invoke_rel', get_printable_location=get_printable_location,
    is_recursive=True)

def invoke_rel(ctx, id, values_input):
    # returns (Ctx.t * value list) option =

    # let _inputs, exps_input, instrs = Ctx.find_rel Local ctx id in
    reld = ctx.find_rel_local(id)
    # check (instrs <> []) id.at "relation has no instructions";
    # let attempt_rules () =
    #   let ctx_local = Ctx.localize ctx in
    ctx_local = ctx.localize()
    #   let ctx_local = Ctx.localize_inputs ctx_local values_input in
    #   let ctx_local = assign_exps ctx_local exps_input values_input in
    ctx_local = assign_exps(ctx_local, reld.exps, values_input)
    #   let ctx_local, sign = eval_instrs ctx_local Cont instrs in
    sign = _rel_eval_instrs(ctx_local, reld)
    #   let ctx = Ctx.commit ctx ctx_local in
    ctx = ctx.commit(sign.sign_get_ctx())
    #   match sign with
    #   | Res values_output ->
    if isinstance(sign, Res):
        return ctx, sign._get_full_list()
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

def _rel_eval_instrs(ctx_local, reld):
    invoke_rel_jit_driver.jit_merge_point(reld=reld)
    try:
        return eval_instrs(ctx_local, reld.instrs)
    except P4Error as e:
        e.traceback_patch_last_name(reld.id.value)
        raise

# ____________________________________________________________
# instructions

@jit.elidable
def instr_tostring(instr):
    return "instr: " + instr.tostring().split("\n")[0]

def eval_instr(ctx, instr):
    #jit.jit_debug(instr_tostring(instr))
    try:
        return instr.eval_instr(ctx)
    except P4Error as e:
        e.maybe_add_region(instr.region)
        e.maybe_add_ctx(ctx)
        raise

@jit.unroll_safe
def eval_instrs(sign, instrs):
    #     eval_instrs (ctx : Ctx.t) (sign : Sign.t) (instrs : instr list) :
    #     Ctx.t * Sign.t =
    #   List.fold_left
    #     (fun (ctx, sign) instr ->
    #       match sign with Sign.Cont -> eval_instr ctx instr | _ -> (ctx, sign))
    #     (ctx, sign) instrs
    for instr in instrs:
        if sign.sign_is_cont():
            sign = eval_instr(sign.sign_get_ctx(), instr)
    return sign

class __extend__(p4specast.IfI):
    def eval_instr(self, ctx):
        # INCOMPLETE
        #     eval_if_instr (ctx : Ctx.t) (exp_cond : exp) (iterexps : iterexp list)
        #     (instrs_then : instr list) (phantom_opt : phantom option) : Ctx.t * Sign.t =
        #   let ctx, cond, value_cond = eval_if_cond_iter ctx exp_cond iterexps in
        ctx, cond = eval_if_cond_iter(ctx, self)
        #   let vid = value_cond.note.vid in
        #   let ctx =
        #     match phantom_opt with
        #     | Some (pid, _) -> Ctx.cover ctx (not cond) pid vid
        #     | None -> ctx
        #   in
        #   if cond then eval_instrs ctx Cont instrs_then else (ctx, Cont)
        if cond:
            return eval_instrs(ctx, self.instrs)
        return ctx

def eval_if_cond_iter(ctx, instr):
    # let iterexps = List.rev iterexps in
    iterexps = instr._get_reverse_iters()
    # eval_if_cond_iter' ctx exp_cond iterexps
    return eval_if_cond_iter_tick(ctx, instr.exp, iterexps)

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
    ctxs_sub = ctx.sub_list(_make_varlist(vars))
    if ctxs_sub.length == 0:
        cond = True
        return ctx, cond
    elif ctxs_sub.length == 1:
        ctx_sub = next(ctxs_sub)
        ctx_sub, cond = eval_if_cond_iter_tick(ctx_sub, exp_cond, iterexps)
        ctx = ctx.commit(ctx_sub)
        return ctx, cond
    return _eval_if_cond_list_loop(ctx, ctxs_sub, exp_cond, iterexps)

def get_printable_location(exp_cond, iterexps, varlist):
    return "eval_if_cond_list_loop %s %s %s" % (exp_cond.tostring(), iterexps.tostring(), varlist.tostring())

jitdriver_eval_if_cond_list_loop = jit.JitDriver(
    reds='auto', greens=['exp_cond', 'iterexps', 'varlist'],
    name='eval_if_cond_list_loop', get_printable_location=get_printable_location)

def _eval_if_cond_list_loop(ctx, ctxs_sub, exp_cond, iterexps):
    cond = True
    for ctx_sub in ctxs_sub:
        jitdriver_eval_if_cond_list_loop.jit_merge_point(exp_cond=exp_cond, iterexps=iterexps, varlist=ctxs_sub.varlist)
        if not cond:
            break
        ctx_sub, cond = eval_if_cond_iter_tick(ctx_sub, exp_cond, iterexps)
        ctx = ctx.commit(ctx_sub)
    return ctx, cond

def eval_if_cond_iter_tick(ctx, exp_cond, iterexps):
    # INCOMPLETE
    # match iterexps with
    # | [] -> eval_if_cond ctx exp_cond
    if iterexps is None:
        return eval_if_cond(ctx, exp_cond)
    else:
    # | iterexp_h :: iterexps_t -> (
    #     let iter_h, vars_h = iterexp_h in
        iterexp = iterexps.head
        iterexps_t = iterexps.tail
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
            ctx, cond = eval_if_cond_list(ctx, exp_cond, vars_h, iterexps_t)
            typ = p4specast.BoolT.INSTANCE.list_of()
            return ctx, cond
    assert 0
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
    # TODO: test it
    iterexp_h, iterexps_t = iterexps.head, iterexps.tail
    iter_h, vars_h = iterexp_h.iter, iterexp_h.vars
    if isinstance(iter_h, p4specast.Opt):
        raise Exception("TODO")
    elif isinstance(iter_h, p4specast.List):
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
        ctx, cond = eval_if_cond_list(ctx, exp_cond, vars_h, iterexps_t)
        # for (id, _typ, iters) in vars_h:
        #     value_sub = ctx.find_value_local(id, iters + [p4specast.List])
        #     # TODO: add edge
        return ctx
    else:
        assert 0, "should be unreachable"

def eval_if_cond(ctx, exp_cond):
    # let ctx, value_cond = eval_exp ctx exp_cond in
    ctx, value_cond = eval_exp(ctx, exp_cond)
    # let cond = Value.get_bool value_cond in
    cond = value_cond.get_bool()
    # (ctx, cond, value_cond)
    return ctx, cond


@jit.unroll_safe
def eval_cases(ctx, exp, cases, cases_exps):
    # returns  Ctx.t * instr list option * value =
    # cases
    block_match = None
    #values_cond = []
    # |> List.fold_left
    for i, case in enumerate(cases):
        #  (fun (ctx, block_match, values_cond) (guard, block) ->
        #    match block_match with
        #    | Some _ -> (ctx, block_match, values_cond)
        #    | None ->
    #            let exp_cond =
    #              match guard with
        exp_cond = cases_exps[i]

        #        in
        #        let exp_cond = exp_cond $$ (exp.at, Il.Ast.BoolT) in
        #        let ctx, value_cond = eval_exp ctx exp_cond in
        ctx, value_cond = eval_exp(ctx, exp_cond)
        #        let values_cond = values_cond @ [ value_cond ] in
        #values_cond.append(values_cond)
        #        let cond = Value.get_bool value_cond in
        cond = value_cond.get_bool()
        #        if cond then (ctx, Some block, values_cond)
        if cond:
            block_match = case.instrs
            break
        #        else (ctx, None, values_cond))
        else:
            assert block_match is None
    #      (ctx, None, [])
    # |> fun (ctx, block_match, values_cond) ->
    # let value_cond =
    #   let vid = Value.fresh () in
    #   let typ = Il.Ast.IterT (Il.Ast.BoolT $ no_region, Il.Ast.List) in
    #   Il.Ast.(ListV values_cond $$$ { vid; typ })
    # in
    # Ctx.add_node ctx value_cond;
    # (ctx, block_match, value_cond)
    return ctx, block_match

class __extend__(p4specast.CaseI):
    def eval_instr(self, ctx):
        # let ctx, instrs_opt, value_cond = eval_cases ctx exp cases in
        ctx, instrs_opt = eval_cases(ctx, self.exp, self.cases, self.cases_exps)
        # let vid = value_cond.note.vid in
        # let ctx =
        #   match phantom_opt with
        #   | Some (pid, _) -> Ctx.cover ctx (Option.is_none instrs_opt) pid vid
        #   | None -> ctx
        # in
        # match instrs_opt with
        # | Some instrs -> eval_instrs ctx Cont instrs
        if instrs_opt is not None:
            return eval_instrs(ctx, instrs_opt)
        # | None -> (ctx, Cont)
        return ctx

class __extend__(p4specast.OtherwiseI):
    def eval_instr(self, ctx):
        return self.instr.eval_instr(ctx)

class __extend__(p4specast.LetI):
    def eval_instr(self, ctx):
        # let ctx = eval_let_iter ctx exp_l exp_r iterexps in
        # (ctx, Cont)
        ctx = eval_let_iter(ctx, self)
        return ctx

@jit.unroll_safe
def _make_varlist(vars):
    varlist = VARLIST_ROOT
    for var in vars:
        varlist = varlist.add_var(var)
    return varlist

@jit.unroll_safe
def _discriminate_bound_binding_variables(ctx, vars):
    vars_bound_list = VARLIST_ROOT
    vars_binding_list = VARLIST_ROOT
    for var in vars:
        if ctx.bound_value_local(var.id, var.iter.append_list()):
            vars_bound_list = vars_bound_list.add_var(var)
        else:
            vars_binding_list = vars_binding_list.add_var(var)
    return vars_bound_list, vars_binding_list

@jit.unroll_safe
def eval_let_list(ctx, exp_l, exp_r, vars_h, iterexps_t):
    # (* Discriminate between bound and binding variables *)
    # let vars_bound, vars_binding =
    #   List.partition
    #     (fun (id, _typ, iters) ->
    #       Ctx.bound_value Local ctx (id, iters @ [ Il.Ast.List ]))
    #     vars
    # in
    vars_bound_list, vars_binding_list = _discriminate_bound_binding_variables(ctx, vars_h)
    # (* Create a subcontext for each batch of bound values *)
    # let ctxs_sub = Ctx.sub_list ctx vars_bound in
    ctxs_sub = ctx.sub_list(vars_bound_list)
    # let ctx, values_binding =
    #   match ctxs_sub with
    #   (* If the bound variable supposed to guide the iteration is already empty,
    #      then the binding variables are also empty *)
    #   | [] ->
    #       let values_binding =
    #         List.init (List.length vars_binding) (fun _ -> [])
    #       in
    #       (ctx, values_binding)
    if ctxs_sub.length == 0:
        values_binding = [[] for _ in vars_binding_list.vars]
    elif ctxs_sub.length == 1:
        ctx_sub = next(ctxs_sub)
        ctx_sub = eval_let_iter_tick(ctx_sub, exp_l, exp_r, iterexps_t)
        ctx = ctx.commit(ctx_sub)
        values_binding = [[ctx_sub.find_value_local(var_binding.id, var_binding.iter)]
                          for var_binding in vars_binding_list.vars]
    #   (* Otherwise, evaluate the premise for each batch of bound values,
    #      and collect the resulting binding batches *)
    #   | _ ->
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
    else:
        ctx, values_binding = _eval_let_list_loop(ctx, ctxs_sub, vars_binding_list, exp_l, exp_r, iterexps_t)
    #       let values_binding = values_binding_batch |> Ctx.transpose in
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
    return _make_lists_and_assign(ctx, vars_binding_list, values_binding)

def get_printable_location(exp_l, exp_r, vars_binding_list):
    return "eval_let_list_loop %s %s %s" % (exp_l.tostring(), exp_r.tostring(), vars_binding_list.tostring())

jitdriver_eval_let_list_loop = jit.JitDriver(
    reds='auto', greens=['exp_l', 'exp_r', 'vars_binding_list'],
    should_unroll_one_iteration = lambda exp_l, exp_r, vars_binding_list: True,
    name='eval_let_list_loop', get_printable_location=get_printable_location)

def _eval_let_list_loop(ctx, ctxs_sub, vars_binding_list, exp_l, exp_r, iterexps_t):
    values_binding = [[None] * ctxs_sub.length for _ in vars_binding_list.vars]
    j = 0
    for ctx_sub in ctxs_sub:
        jitdriver_eval_let_list_loop.jit_merge_point(exp_l=exp_l, exp_r=exp_r, vars_binding_list=vars_binding_list)
        ctx_sub = eval_let_iter_tick(ctx_sub, exp_l, exp_r, iterexps_t)
        ctx = ctx.commit(ctx_sub)
        for i, var_binding in enumerate(vars_binding_list.vars):
            value_binding = ctx_sub.find_value_local(var_binding.id, var_binding.iter)
            values_binding[i][j] = value_binding
        j += 1
    return ctx, values_binding


def eval_let_iter_tick(ctx, exp_l, exp_r, iterexps):
    # INCOMPLETE
    # TODO: should test it
    # match iterexps with
    # | [] -> eval_let ctx exp_l exp_r
    if iterexps is None:
        return eval_let(ctx, exp_l, exp_r)
    # | iterexp_h :: iterexps_t -> (
    else:
        iterexp = iterexps.head
        iterexps_t = iterexps.tail
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
    #import pdb;pdb.set_trace()
    raise P4EvaluationError("todo eval_let_iter_tick")

def eval_let_iter(ctx, let_instr):
    # let iterexps = List.rev iterexps in
    iterexps = let_instr._get_reverse_iters()
    # eval_let_iter' ctx exp_l exp_r iterexps
    return eval_let_iter_tick(ctx, let_instr.var, let_instr.value, iterexps)

def eval_let(ctx, exp_l, exp_r):
    # let ctx, value = eval_exp ctx exp_r in
    ctx, value = eval_exp(ctx, exp_r)
    # assign_exp ctx exp_l value
    return assign_exp(ctx, exp_l, value)

def eval_let_opt(ctx, exp_l, exp_r, vars, iterexps):
    #import pdb; pdb.set_trace()
    raise P4EvaluationError("TODO; implement eval_let_opt")
    # and eval_let_opt (ctx : Ctx.t) (exp_l : exp) (exp_r : exp) (vars : var list)
    #     (iterexps : iterexp list) : Ctx.t =
    #   (* Discriminate between bound and binding variables *)
    #   let vars_bound, vars_binding =
    #     List.partition
    #       (fun (id, _typ, iters) ->
    #         Ctx.bound_value Local ctx (id, iters @ [ Il.Ast.Opt ]))
    #       vars
    #   in
    #   let ctx_sub_opt = Ctx.sub_opt ctx vars_bound in
    #   let ctx, values_binding =
    #     match ctx_sub_opt with
    #     (* If the bound variable supposed to guide the iteration is already empty,
    #        then the binding variables are also empty *)
    #     | None ->
    #         let values_binding =
    #           List.map
    #             (fun (_id_binding, typ_binding, iters_binding) ->
    #               let value_binding =
    #                 let vid = Value.fresh () in
    #                 let typ =
    #                   Typ.iterate typ_binding (iters_binding @ [ Il.Ast.Opt ])
    #                 in
    #                 Il.Ast.(OptV None $$$ { vid; typ = typ.it })
    #               in
    #               Ctx.add_node ctx value_binding;
    #               List.iter
    #                 (fun (id, _typ, iters) ->
    #                   let value_sub =
    #                     Ctx.find_value Local ctx (id, iters @ [ Il.Ast.Opt ])
    #                   in
    #                   Ctx.add_edge ctx value_binding value_sub Dep.Edges.Iter)
    #                 vars_bound;
    #               value_binding)
    #             vars_binding
    #         in
    #         (ctx, values_binding)
    #     (* Otherwise, evaluate the premise for the subcontext *)
    #     | Some ctx_sub ->
    #         let ctx_sub = eval_let_iter' ctx_sub exp_l exp_r iterexps in
    #         let ctx = Ctx.commit ctx ctx_sub in
    #         let values_binding =
    #           List.map
    #             (fun (id_binding, typ_binding, iters_binding) ->
    #               let value_binding =
    #                 Ctx.find_value Local ctx_sub (id_binding, iters_binding)
    #               in
    #               let value_binding =
    #                 let vid = Value.fresh () in
    #                 let typ =
    #                   Typ.iterate typ_binding (iters_binding @ [ Il.Ast.Opt ])
    #                 in
    #                 Il.Ast.(OptV (Some value_binding) $$$ { vid; typ = typ.it })
    #               in
    #               Ctx.add_node ctx value_binding;
    #               List.iter
    #                 (fun (id, _typ, iters) ->
    #                   let value_sub =
    #                     Ctx.find_value Local ctx (id, iters @ [ Il.Ast.Opt ])
    #                   in
    #                   Ctx.add_edge ctx value_binding value_sub Dep.Edges.Iter)
    #                 vars_bound;
    #               value_binding)
    #             vars_binding
    #         in
    #         (ctx, values_binding)
    #   in
    #   (* Finally, bind the resulting values *)
    #   List.fold_left2
    #     (fun ctx (id_binding, _typ_binding, iters_binding) value_binding ->
    #       Ctx.add_value Local ctx
    #         (id_binding, iters_binding @ [ Il.Ast.Opt ])
    #         value_binding)
    #     ctx vars_binding values_binding

@jit.unroll_safe
def split_exps_without_idx(inputs, exps):
    if not objectmodel.we_are_translated():
        assert sorted(inputs) == inputs # inputs is sorted
    exps_input = []
    exps_output = []
    for index, exp in enumerate(exps):
        for input in inputs:
            if index == input:
                exps_input.append(exp)
                break
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
    exps = notexp.exps
    exps_input, exps_output = split_exps_without_idx(inputs, exps)
    #   let ctx, values_input = eval_exps ctx exps_input in
    ctx, values_input = eval_exps(ctx, exps_input)
    #   let ctx, values_output =
    #     match invoke_rel ctx id values_input with
    #     | Some (ctx, values_output) -> (ctx, values_output)
    #     | None -> error id.at "relation was not matched"
    relctx, values_output = invoke_rel(ctx, id, values_input)
    if relctx is None:
        raise P4RelationError("relation was not matched: %s" % id.value)
    ctx = relctx
    #   assign_exps ctx exps_output values_output
    ctx = assign_exps(ctx, exps_output, values_output)
    return ctx

@jit.unroll_safe
def eval_rule_list(ctx, id, notexp, vars, iterexps):
    # INCOMPLETE, a lot of copy-pasted code from eval_let_list
    # (* Discriminate between bound and binding variables *)
    # let vars_bound, vars_binding =
    #   List.partition
    #     (fun (id, _typ, iters) ->
    #       Ctx.bound_value Local ctx (id, iters @ [ Il.Ast.List ]))
    #     vars
    # in
    vars_bound_list, vars_binding_list = _discriminate_bound_binding_variables(ctx, vars)
    # (* Create a subcontext for each batch of bound values *)
    # let ctxs_sub = Ctx.sub_list ctx vars_bound in
    ctxs_sub = ctx.sub_list(vars_bound_list)
    # let ctx, values_binding =
    #   match ctxs_sub with
    #   (* If the bound variable supposed to guide the iteration is already empty,
    #      then the binding variables are also empty *)
    #   | [] ->
    if ctxs_sub.length <= 1:
        if ctxs_sub.length == 0:
        #       let values_binding =
        #         List.init (List.length vars_binding) (fun _ -> [])
        #       in
        #       (ctx, values_binding)
            values_binding = [
                var_binding.typ.iterate(var_binding.iter.append_list()).empty_list_value()
                for var_binding in vars_binding_list.vars]
        #   (* Otherwise, evaluate the premise for each batch of bound values,
        #      and collect the resulting binding batches *)
        #   | _ ->
        else:
            assert ctxs_sub.length == 1
            ctx_sub = next(ctxs_sub)
            ctx_sub = eval_rule_iter_tick(ctx_sub, id, notexp, iterexps)
            ctx = ctx.commit(ctx_sub)
            values_binding = [None] * len(vars_binding_list.vars)
            for i, var_binding in enumerate(vars_binding_list.vars):
                iters_binding = var_binding.iter
                list_typ = var_binding.typ.iterate(iters_binding.append_list())
                value_binding = ctx_sub.find_value_local(var_binding.id, var_binding.iter)
                values_binding[i] = objects.ListV.make1(value_binding, list_typ)
        #       in
        #       let values_binding = values_binding_batch |> Ctx.transpose in
            assert len(values_binding) == len(vars_binding_list.vars)
        return _dont_make_lists_and_assign(ctx, vars_binding_list, values_binding)
    else:
    #       let ctx, values_binding_batch =
    #         List.fold_left
    #           (fun (ctx, values_binding_batch) ctx_sub ->
    #             let ctx_sub = eval_rule_iter' ctx_sub id notexp iterexps in
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
        ctx, values_binding = _eval_rule_list_loop(ctx, id, notexp, iterexps, vars_binding_list, ctxs_sub)
    #       (ctx, values_binding)
    return _make_lists_and_assign(ctx, vars_binding_list, values_binding)

@jit.unroll_safe
def _make_lists_and_assign(ctx, vars_binding_list, values_binding):
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
    #   ctx vars_binding values_binding
    for index, values_binding in enumerate(values_binding):
        var_binding = vars_binding_list.vars[index]
        id_binding = var_binding.id
        typ_binding = var_binding.typ
        iters_binding = var_binding.iter
        iters_binding_list = iters_binding.append_list()
        list_typ = typ_binding.iterate(iters_binding_list)
        value_binding = objects.ListV.make(values_binding, list_typ)
        ctx = ctx.add_value_local(id_binding, iters_binding_list, value_binding)
    return ctx

@jit.unroll_safe
def _dont_make_lists_and_assign(ctx, vars_binding_list, values_binding):
    for index, value_binding in enumerate(values_binding):
        var_binding = vars_binding_list.vars[index]
        id_binding = var_binding.id
        iters_binding = var_binding.iter
        ctx = ctx.add_value_local(id_binding, iters_binding.append_list(), value_binding)
    return ctx


def get_printable_location(id, notexp, vars_binding_list):
    return "eval_rule_list_loop %s %s %s" % (id.tostring(), notexp.tostring(), vars_binding_list.tostring())

jitdriver_eval_rule_list_loop = jit.JitDriver(
    reds='auto', greens=['id', 'notexp', 'vars_binding_list'],
    name='eval_rule_list_loop', get_printable_location=get_printable_location)

def _eval_rule_list_loop(ctx, id, notexp, iterexps, vars_binding_list, ctxs_sub):
    values_binding = [[None] * ctxs_sub.length for _ in vars_binding_list.vars]
    j = 0
    for ctx_sub in ctxs_sub:
        jitdriver_eval_rule_list_loop.jit_merge_point(id=id, notexp=notexp, vars_binding_list=vars_binding_list)
        ctx_sub = eval_rule_iter_tick(ctx_sub, id, notexp, iterexps)
        ctx = ctx.commit(ctx_sub)
        for i, var_binding in enumerate(vars_binding_list.vars):
            value_binding = ctx_sub.find_value_local(var_binding.id, var_binding.iter)
            values_binding[i][j] = value_binding
        j += 1
    #       in
    #       let values_binding = values_binding_batch |> Ctx.transpose in
    assert len(values_binding) == len(vars_binding_list.vars)
    return ctx,values_binding


def eval_rule_iter_tick(ctx, id, notexp, iterexps):
    # match iterexps with
    #   match iterexps with
    #   | [] -> eval_rule ctx id notexp
    if not iterexps:
        return eval_rule(ctx, id, notexp)
    #   | iterexp_h :: iterexps_t -> (
    #       let iter_h, vars_h = iterexp_h in
    #       match iter_h with
    #       | Opt -> eval_rule_opt ctx id notexp vars_h iterexps_t
    #       | List -> eval_rule_list ctx id notexp vars_h iterexps_t)
    iterexp = iterexps.head
    iterexps_t = iterexps.tail
    iter_h = iterexp.iter
    vars_h = iterexp.vars
    if isinstance(iter_h, p4specast.Opt):
        raise P4EvaluationError("TODO eval_rule_iter_tick")
        return eval_rule_opt(ctx, id, notexp, vars_h, iterexps_t)
    if isinstance(iter_h, p4specast.List):
        return eval_rule_list(ctx, id, notexp, vars_h, iterexps_t)
    else:
        assert False, "unknown iter_h: %s" % iter_h

def eval_rule_iter(ctx, instr):
    # let iterexps = List.rev iterexps in
    # eval_rule_iter' ctx id notexp iterexps
    iterexps = instr._get_reverse_iters()
    return eval_rule_iter_tick(ctx, instr.id, instr.notexp, iterexps)

class __extend__(p4specast.RuleI):
    def eval_instr(self, ctx):
        # let ctx = eval_rule_iter ctx id notexp iterexps in
        try:
            ctx = eval_rule_iter(ctx, self)
        except P4Error as e:
            e.traceback_add_frame('???', self.region, self)
            raise
        return ctx


def eval_hold_cond(ctx, id, notexp):
    #and eval_hold_cond (ctx : Ctx.t) (id : id) (notexp : notexp) :
    #    Ctx.t * bool * value =
    #  let _, exps_input = notexp in
    exps_input = notexp.exps
    #  let ctx, values_input = eval_exps ctx exps_input in
    ctx, values_input = eval_exps(ctx, exps_input)
    #  let ctx, hold =
    #    match invoke_rel ctx id values_input with
    #    | Some (ctx, _) -> (ctx, true)
    #    | None -> (ctx, false)
    result_ctx, values = invoke_rel(ctx, id, values_input)
    if result_ctx is not None:
        ctx = result_ctx
        hold = True
    else:
        hold = False
    #  in
    #  let value_res =
    #    let vid = Value.fresh () in
    #    let typ = Il.Ast.BoolT in
    #    Il.Ast.(BoolV hold $$$ { vid; typ })
    #  in
    #  Ctx.add_node ctx value_res;
    #  List.iteri
    #    (fun idx value_input ->
    #      Ctx.add_edge ctx value_res value_input (Dep.Edges.Rel (id, idx)))
    #    values_input;
    #  (ctx, hold, value_res)
    return ctx, hold

def eval_hold_cond_list(ctx, id, notexp, vars, iterexps):
    #and eval_hold_cond_list (ctx : Ctx.t) (id : id) (notexp : notexp)
    #    (vars : var list) (iterexps : iterexp list) : Ctx.t * bool * value list =
    #  let ctxs_sub = Ctx.sub_list ctx vars in
    ctxs_sub = ctx.sub_list(_make_varlist(vars))
    #  List.fold_left
    #    (fun (ctx, cond, values_cond) ctx_sub ->
    #      if not cond then (ctx, cond, values_cond)
    #      else
    #        let ctx_sub, cond, value_cond =
    #          eval_hold_cond_iter' ctx_sub id notexp iterexps
    #        in
    #        let ctx = Ctx.commit ctx ctx_sub in
    #        let values_cond = values_cond @ [ value_cond ] in
    #        (ctx, cond, values_cond))
    #    (ctx, true, []) ctxs_sub
    if ctxs_sub.length == 0:
        return ctx, True
    elif ctxs_sub.length == 1:
        ctx_sub = next(ctxs_sub)
        ctx_sub, cond = eval_hold_cond_iter_tick(ctx_sub, id, notexp, iterexps)
        ctx = ctx.commit(ctx_sub)
        return ctx, cond
    return _eval_hold_cond_list_loop(ctx, ctxs_sub, id, notexp, iterexps)

def get_printable_location(id, notexp, iterexps, varlist):
    return "eval_hold_cond_list_loop %s %s %s %s" % (id.value, notexp.tostring(), iterexps.tostring(), varlist.tostring())

jitdriver_eval_hold_cond_list_loop = jit.JitDriver(
    reds='auto', greens=['id', 'notexp', 'iterexps', 'varlist'],
    name='eval_hold_cond_list_loop', get_printable_location=get_printable_location)

def _eval_hold_cond_list_loop(ctx, ctxs_sub, id, notexp, iterexps):
    cond = True
    for ctx_sub in ctxs_sub:
        jitdriver_eval_hold_cond_list_loop.jit_merge_point(id=id, notexp=notexp, iterexps=iterexps, varlist=ctxs_sub.varlist)
        if not cond:
            break
        ctx_sub, cond_sub = eval_hold_cond_iter_tick(ctx_sub, id, notexp, iterexps)
        ctx = ctx.commit(ctx_sub)
        cond = cond_sub
    return ctx, cond

def eval_hold_cond_iter_tick(ctx, id, notexp, iterexps):
    #and eval_hold_cond_iter' (ctx : Ctx.t) (id : id) (notexp : notexp)
    #    (iterexps : iterexp list) : Ctx.t * bool * value =
    #  match iterexps with
    #  | [] -> eval_hold_cond ctx id notexp
    if not iterexps:
        return eval_hold_cond(ctx, id, notexp)
    #  | iterexp_h :: iterexps_t -> (
    iterexp_h = iterexps.head
    iterexps_t = iterexps.tail
    #      let iter_h, vars_h = iterexp_h in
    iter_h = iterexp_h.iter
    vars_h = iterexp_h.vars
    #      match iter_h with
    #      | Opt -> error no_region "(TODO)"
    if isinstance(iter_h, p4specast.Opt):
        raise P4NotImplementedError("(TODO) eval_hold_cond_iter Opt")
    #      | List ->
    elif isinstance(iter_h, p4specast.List):
    #          let ctx, cond, values_cond =
    #            eval_hold_cond_list ctx id notexp vars_h iterexps_t
        ctx, cond = eval_hold_cond_list(ctx, id, notexp, vars_h, iterexps_t)
    #          in
    #          let value_cond =
    #            let vid = Value.fresh () in
    #            let typ = Il.Ast.IterT (Il.Ast.BoolT $ no_region, Il.Ast.List) in
    #            Il.Ast.(ListV values_cond $$$ { vid; typ })
    #          in
    #          Ctx.add_node ctx value_cond;
    #          List.iter
    #            (fun (id, _typ, iters) ->
    #              let value_sub =
    #                Ctx.find_value Local ctx (id, iters @ [ Il.Ast.List ])
    #              in
    #              Ctx.add_edge ctx value_cond value_sub Dep.Edges.Iter)
    #            vars_h;
    #          (ctx, cond, value_cond))
        return ctx, cond
    else:
        assert False, "unknown iter_h type: %s" % iter_h.__class__.__name__

def eval_hold_cond_iter(ctx, instr):
    #and eval_hold_cond_iter (ctx : Ctx.t) (id : id) (notexp : notexp)
    #    (iterexps : iterexp list) : Ctx.t * bool * value =
    #  let iterexps = List.rev iterexps in
    iterexps = instr._get_reverse_iters()
    #  eval_hold_cond_iter' ctx id notexp iterexps
    return eval_hold_cond_iter_tick(ctx, instr.id, instr.notexp, iterexps)

#
class __extend__(p4specast.HoldI):
    def eval_instr(self, ctx):
        #and eval_hold_instr (ctx : Ctx.t) (id : id) (notexp : notexp)
        #    (iterexps : iterexp list) (holdcase : holdcase) : Ctx.t * Sign.t =
        #  (* Copy the current coverage information *)
        #  let cover_backup = !(ctx.cover) in
        #  (* Evaluate the hold condition *)
        #  let ctx, cond, value_cond = eval_hold_cond_iter ctx id notexp iterexps in
        ctx, cond = eval_hold_cond_iter(ctx, self)
        #  (* Evaluate the hold case, and restore the coverage information
        #     if the expected behavior is the relation not holding *)
        #  let vid = value_cond.note.vid in
        #  match holdcase with
        #  | BothH (instrs_hold, instrs_not_hold) ->
        holdcase = self.holdcase
        if isinstance(holdcase, p4specast.BothH):
        #      if cond then eval_instrs ctx Cont instrs_hold
            if cond:
                return eval_instrs(ctx, holdcase.hold_instrs)
        #      else (
        #        ctx.cover := cover_backup;
        #        eval_instrs ctx Cont instrs_not_hold)
            else:
                return eval_instrs(ctx, holdcase.nothold_instrs)
        #  | HoldH (instrs_hold, phantom_opt) ->
        elif isinstance(holdcase, p4specast.HoldH):
        #      let ctx =
        #        match phantom_opt with
        #        | Some (pid, _) -> Ctx.cover ctx (not cond) pid vid
        #        | None -> ctx
        #      in
        #      if cond then eval_instrs ctx Cont instrs_hold else (ctx, Cont)
            if cond:
                return eval_instrs(ctx, holdcase.hold_instrs)
            else:
                return ctx
        #  | NotHoldH (instrs_not_hold, phantom_opt) ->
        elif isinstance(holdcase, p4specast.NotHoldH):
        #      ctx.cover := cover_backup;
        #      let ctx =
        #        match phantom_opt with
        #        | Some (pid, _) -> Ctx.cover ctx cond pid vid
        #        | None -> ctx
        #      in
        #      if not cond then eval_instrs ctx Cont instrs_not_hold else (ctx, Cont)
            if not cond:
                return eval_instrs(ctx, holdcase.nothold_instrs)
            else:
                return ctx
        else:
            assert False, "unknown holdcase type: %s" % self.holdcase.__class__.__name__

@jit.unroll_safe
def assign_exp(ctx, exp, value):
    # let note = value.note.typ in
    # match (exp.it, value.it) with
    if isinstance(exp, p4specast.VarE):
    # | VarE id, _ ->
    #     let ctx = Ctx.add_value Local ctx (id, []) value in
        ctx = ctx.add_value_local(exp.id, p4specast.IterList.EMPTY, value, vare_cache=exp)
        return ctx
    #     ctx
    # | TupleE exps_inner, TupleV values_inner ->
    elif isinstance(exp, p4specast.TupleE) and \
         isinstance(value, objects.TupleV):
    #     let ctx = assign_exps ctx exps_inner values_inner in
        exps_inner = exp.elts
        values_inner = value.get_tuple()
        ctx = assign_exps(ctx, exps_inner, values_inner)
    #     List.iter
    #       (fun value_inner -> Ctx.add_edge ctx value_inner value Dep.Edges.Assign)
    #       values_inner;
    #     ctx
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
        ctx = assign_exps_casev(ctx, exp.notexp, value)
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
    elif isinstance(exp, p4specast.OptE) and \
         isinstance(value, objects.OptV):
        if exp.exp is not None and value.value is not None:
            ctx = assign_exp(ctx, exp.exp, value.value)
            return ctx
        elif exp.exp is None and value.value is None:
            return ctx
        else:
            assert False, "mismatched OptE and OptV"
    # | ListE exps_inner, ListV values_inner ->
    if isinstance(exp, p4specast.ListE) and \
       isinstance(value, objects.ListV):
    #     let ctx = assign_exps ctx exps_inner values_inner in
        ctx = assign_exps(ctx, exp.elts, value.get_list())
    #     List.iter
    #       (fun value_inner -> Ctx.add_edge ctx value_inner value Dep.Edges.Assign)
    #       values_inner;
    #     ctx
        return ctx
    # | ConsE (exp_h, exp_t), ListV values_inner ->
    elif isinstance(exp, p4specast.ConsE) and \
         isinstance(value, objects.ListV):
        values_inner = value.get_list()
        assert values_inner, "cannot assign empty list to ConsE"
    #     let value_h = List.hd values_inner in
        value_h = values_inner[0]
    #     let value_t =
    #       let vid = Value.fresh () in
    #       let typ = note in
    #       Il.Ast.(ListV (List.tl values_inner) $$$ { vid; typ })
        value_t = objects.ListV.make(values_inner[1:], value.get_typ())
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
                typ = var.typ.iterate(var.iter.append_opt())
                value_sub = typ.opt_none_value()
                ctx = ctx.add_value_local(var.id, var.iter.append_opt(), value_sub)
            return ctx
    # | IterE (exp, (Opt, vars)), OptV (Some value) ->
        else:
    #     (* Assign the value to the iterated expression *)
    #     let ctx = assign_exp ctx exp value in
            ctx = assign_exp(ctx, exp.exp, value.value)
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
            for var in exp.varlist:
                value_sub_inner = ctx.find_value_local(var.id, var.iter)
                typ = var.typ.iterate(var.iter.append_opt())
                value_sub = objects.OptV(value_sub_inner, typ)
                ctx = ctx.add_value_local(var.id, var.iter.append_opt(), value_sub)
            return ctx
    elif (isinstance(exp, p4specast.IterE) and
          exp.is_simple_list_expr() and
          isinstance(value, objects.ListV)):
        return ctx.add_value_local(exp.varlist[0].id, exp.varlist[0].iter.append_list(), value)
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
    #     in
        values = value.get_list()
        if len(values) == 0:
            for var in exp.varlist:
                # create a ListV value for these
                listtyp = var.typ.iterate(var.iter.append_list())
                value_sub = listtyp.empty_list_value()
                ctx = ctx.add_value_local(var.id, var.iter.append_list(), value_sub)
            return ctx
        elif len(values) == 1:
            value_elem, = values
            ctx_local = ctx.localize_empty_venv()
            ctx_local = assign_exp(ctx_local, exp.exp, value_elem)
            for var in exp.varlist:
                # collect elementwise values from each ctx in ctxs
                newvalue = ctx_local.find_value_local(var.id, var.iter)
                # create a ListV value for these
                listtyp = var.typ.iterate(var.iter.append_list())
                value_sub = objects.ListV.make1(newvalue, listtyp)
                ctx = ctx.add_value_local(var.id, var.iter.append_list(), value_sub)
            return ctx
        else:
            ctx_local = ctx.localize()
            values = _assign_exp_iter_cases(ctx_local, exp, values)
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
            for i, var in enumerate(exp.varlist):
                # collect elementwise values from each ctx in ctxs
                # create a ListV value for these
                listtyp = var.typ.iterate(var.iter.append_list())
                value_sub = objects.ListV.make(values[i], listtyp)
                ctx = ctx.add_value_local(var.id, var.iter.append_list(), value_sub)
            return ctx

    # | _ ->
    #     error exp.at
    #       (F.asprintf "(TODO) match failed %s <- %s"
    #          (Sl.Print.string_of_exp exp)
    #          (Sl.Print.string_of_value ~short:true value))
    #import pdb;pdb.set_trace()
    raise P4EvaluationError("todo assign_exp: unhandled expression type %s" % exp.__class__.__name__)

def get_printable_location(exp):
    return "assign_exp_iter_cases %s" % (exp.tostring())

jitdriver_assign_exp_iter_cases = jit.JitDriver(
    reds='auto', greens=['exp'],
    name='assign_exp_iter_cases', get_printable_location=get_printable_location)


def _assign_exp_iter_cases(ctx_local, exp, values):
    # this is basically an unzip
    values_result = [[None] * len(values) for _ in exp.varlist]
    i = 0
    while 1:
        jitdriver_assign_exp_iter_cases.jit_merge_point(exp=exp)
        if i >= len(values):
            break
        value_elem = values[i]
        ctx_local2 = assign_exp(ctx_local, exp.exp, value_elem)
        for index, var in enumerate(exp.varlist):
            values_result[index][i] = ctx_local2.find_value_local(var.id, var.iter)
        i += 1
    return values_result

@jit.unroll_safe
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
    assert len(exps) == len(values), \
        "mismatch in number of expressions and values while assigning, expected %d value(s) but got %d" % (len(exps), len(values))
    for index, exp in enumerate(exps):
        value = values[index]
        ctx = assign_exp(ctx, exp, value)
    return ctx


@jit.unroll_safe
def assign_exps_casev(ctx, notexp, casev):
    exps = notexp.exps
    assert len(exps) == casev._get_size_list(), \
        "mismatch in number of expressions and values while assigning, expected %d value(s) but got %d" % (len(exps), casev._get_size_list())
    ctx2 = None
    if notexp.is_simple_casev_assignment_target():
        ctx2 = ctx.try_append_case_values(notexp, casev)
        if ctx2 is not None:
            return ctx2
    for index, exp in enumerate(exps):
        value = casev._get_list(index)
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

@jit.unroll_safe
def assign_args(ctx_caller, ctx_callee, func, values):
    if len(func.args) != len(values):
        raise P4EvaluationError("mismatch in number of arguments while assigning, expected %d value(s) but got %d for func %s" % (len(func.args), len(values), func.id.value))
    assert ctx_callee._get_size_list() == 0
    if func._simple_args:
        venv_keys = _compute_final_env_keys(func, jit.promote(ctx_callee.venv_keys))
        ctx_callee = ctx_callee.copy_and_change_set_list(values, venv_keys)
    else:
        for i, arg in enumerate(func.args):
            value = values[i]
            ctx_callee = assign_arg(ctx_caller, ctx_callee, arg, value)
    return ctx_callee

@jit.elidable
def _compute_final_env_keys(func, venv_keys):
    if func._ctx_env_args_start is venv_keys:
        return func._ctx_env_args_end
    func._ctx_env_args_start = venv_keys
    for arg in func.args:
        assert isinstance(arg, p4specast.ExpA)
        exp = arg.exp
        assert isinstance(exp, p4specast.VarE)
        venv_keys = venv_keys.add_key(exp.id.value)
    func._ctx_env_args_end = venv_keys
    return venv_keys


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

class __extend__(p4specast.ResultI):
    def eval_instr(self, ctx):
        # type: (p4specast.ResultI, context.Context) -> tuple[context.Context, Res]
        #  let ctx, values = eval_exps ctx exps in
        #  (ctx, Res values)
        if not self.exps:
            return Res.make0(ctx)
        ctx, values = eval_exps(ctx, self.exps)
        return Res.make(values, ctx)

class __extend__(p4specast.ReturnI):
    def eval_instr(self, ctx):
        # let ctx, value = eval_exp ctx exp in
        # (ctx, Ret value)
        ctx, value = eval_exp(ctx, self.exp)
        return Ret(ctx, value)

# ____________________________________________________________
# expressions

@jit.elidable
def exp_tostring(exp):
    return "exp:" + exp.tostring()

def eval_exp(ctx, exp):
    return exp.eval_exp(ctx)

@jit.unroll_safe
def eval_exps(ctx, exps):
    # List.fold_left
    #   (fun (ctx, values) exp ->
    #     let ctx, value = eval_exp ctx exp in
    #     (ctx, values @ [ value ]))
    #   (ctx, []) exps
    values = [None] * len(exps)
    for i, exp in enumerate(exps):
        ctx, value = eval_exp(ctx, exp)
        values[i] = value
    return ctx, values

class __extend__(p4specast.Exp):
    def eval_exp(self, ctx):
        #import pdb;pdb.set_trace()
        raise P4NotImplementedError("abstract base class %s" % self)

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
        return ctx, objects.BoolV.make(self.value, self.typ)

class __extend__(p4specast.NumE):
    def eval_exp(self, ctx):
        return ctx, objects.NumV.make(self.value, self.what, typ=self.typ)

class __extend__(p4specast.TextE):
    def eval_exp(self, ctx):
        return ctx, objects.TextV(self.value, self.typ)

class __extend__(p4specast.VarE):
    def eval_exp(self, ctx):
        # let value = Ctx.find_value Local ctx (id, []) in
        value = ctx.find_value_local(self.id, vare_cache=self)
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
        value_res = self.typ.make_opt_value(value)
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
        value_res = objects.TupleV.make(values, self.typ)
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
        if not self.elts:
            return ctx, self.typ.empty_list_value()
        if len(self.elts) == 1:
            ctx, value = eval_exp(ctx, self.elts[0])
            value_res = objects.ListV.make1(value, self.typ)
        else:
            ctx, values = eval_exps(ctx, self.elts)
            #   let value_res =
            #     let vid = Value.fresh () in
            #     let typ = note in
            #     Il.Ast.(ListV values $$$ { vid; typ })
            value_res = objects.ListV.make(values, self.typ)
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
    return objects.BoolV.make(value, typ)

class __extend__(p4specast.ConsE):
    def eval_exp(self, ctx):
        # and eval_cons_exp (note : typ') (ctx : Ctx.t) (exp_h : exp) (exp_t : exp) :
        #     Ctx.t * value =
        #   let ctx, value_h = eval_exp ctx exp_h in
        #   let ctx, value_t = eval_exp ctx exp_t in
        #   let values_t = Value.get_list value_t in
        #   let value_res =
        #     let vid = Value.fresh () in
        #     let typ = note in
        #     Il.Ast.(ListV (value_h :: values_t) $$$ { vid; typ })
        #   in
        #   Ctx.add_node ctx value_res;
        #   (ctx, value_res)
        exp_h = self.head
        exp_t = self.tail
        ctx, value_h = eval_exp(ctx, exp_h)
        ctx, value_t = eval_exp(ctx, exp_t)
        assert isinstance(value_t, objects.ListV)
        values_t = value_t.get_list()
        value_res = objects.ListV.make([value_h] + values_t, self.typ)
        return ctx, value_res

def eval_cmp_num(cmpop, value_l, value_r, typ):
    # let num_l = Value.get_num value_l in
    assert isinstance(value_l, objects.NumV)
    assert isinstance(value_r, objects.NumV)
    return value_l.eval_cmpop(cmpop, value_r, typ)


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
        res_bool = bool_l and bool_r
    # | `OrOp -> Il.Ast.BoolV (bool_l || bool_r)
    elif binop == 'OrOp':
        res_bool = bool_l or bool_r
    # | `ImplOp -> Il.Ast.BoolV ((not bool_l) || bool_r)
    elif binop == 'ImplOp':
        res_bool = (not bool_l) or bool_r
    # | `EquivOp -> Il.Ast.BoolV (bool_l = bool_r)
    elif binop == 'EquivOp':
        res_bool = bool_l == bool_r
    else:
        assert 0, "should be unreachable"
    return objects.BoolV.make(res_bool, typ)

def eval_binop_num(binop, value_l, value_r, typ):
    # let num_l = Value.get_num value_l in
    # let num_r = Value.get_num value_r in
    # Il.Ast.NumV (Num.bin binop num_l num_r)
    assert isinstance(value_l, objects.NumV)
    assert isinstance(value_r, objects.NumV)
    return value_l.eval_binop(binop, value_r, typ)

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
        return objects.BoolV.make(not value.get_bool(), typ=typ)
    else:
        assert 0, "Unknown boolean unary operator: %s" % unop

def eval_unop_num(unop, value, typ):
    # let num = Value.get_num value in
    assert isinstance(value, objects.NumV)
    return value.eval_unop(unop, typ)

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
        assert isinstance(value_s, objects.ListV)
        #   let value_res =
        #     let vid = Value.fresh () in
        #     let typ = note in
        #     Il.Ast.(BoolV (List.exists (Value.eq value_e) values_s) $$$ { vid; typ })
        if value_s._get_size_list() == 0:
            res = False
        elif value_s._get_size_list() == 1:
            res = value_e.eq(value_s._get_list(0))
        else:
            values_s = value_s.get_list()
            res = _mem_list(value_e, values_s)
        value_res = objects.BoolV.make(res, self.typ)
        return ctx, value_res
        #   in
        #   Ctx.add_node ctx value_res;
        #   Ctx.add_edge ctx value_res value_e (Dep.Edges.Op MemOp);
        #   Ctx.add_edge ctx value_res value_s (Dep.Edges.Op MemOp);
        #   (ctx, value_res)

def _mem_list(value_e, values_s):
    for v in values_s:
        if value_e.eq(v):
            return True
    return False

class __extend__(p4specast.DotE):
    def eval_exp(self, ctx):
        #   let ctx, value_b = eval_exp ctx exp_b in
        ctx, value_b = eval_exp(ctx, self.obj)
        #   let fields = Value.get_struct value_b in
        value_b = value_b.get_struct()
        value = value_b.get_field(self.field)
        return ctx, value
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
        value_res = objects.BoolV.make(sub, note)
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
            len_v = value._get_size_list()
        #       let len_v = List.length values in
        #       match listpattern with
        #       | `Cons -> len_v > 0
            if isinstance(listpattern, p4specast.Cons):
                matches = (len_v > 0)
        #       | `Fixed len_p -> len_v = len_p
            elif isinstance(listpattern, p4specast.Fixed):
                matches = (len_v == listpattern.value)
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
            #import pdb;pdb.set_trace()
            raise P4EvaluationError("TODO MatchE")
        # in
        # let value_res =
        #   let vid = Value.fresh () in
        #   let typ = note in
        #   Il.Ast.(BoolV matches $$$ { vid; typ })
        value_res = objects.BoolV.make(matches, self.typ)
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

class __extend__(p4specast.StrE):
    @jit.unroll_safe
    def eval_exp(self, ctx):
        # let atoms, exps = List.split fields in
        # let ctx, values = eval_exps ctx exps in
        # let fields = List.combine atoms values in
        map = objects.StructMap.EMPTY
        values = [None] * len(self.fields)
        for i, (atom, exp) in enumerate(self.fields):
            ctx, value = eval_exp(ctx, exp)
            map = map.add_field(atom.value)
            values[i] = value
        # let value_res =
        #   let vid = Value.fresh () in
        #   let typ = note in
        #   Il.Ast.(StructV fields $$$ { vid; typ })
        # in
        # Ctx.add_node ctx value_res;
        # if List.length values = 0 then
        #   List.iter
        #     (fun value_input ->
        #       Ctx.add_edge ctx value_res value_input Dep.Edges.Control)
        #     ctx.local.values_input;
        # (ctx, value_res)
        return ctx, objects.StructV.make(values, map, self.typ)

class __extend__(p4specast.CaseE):
    def eval_exp(self, ctx):
        # let mixop, exps = notexp in
        mixop = self.notexp.mixop
        exps = self.notexp.exps
        # let ctx, values = eval_exps ctx exps in
        if len(exps) == 0:
            value_res = objects.CaseV.make0(mixop, self.typ)
        elif len(exps) == 1:
            ctx, value = eval_exp(ctx, exps[0])
            value_res = objects.CaseV.make1(value, mixop, self.typ)
        else:
            ctx, values = eval_exps(ctx, exps)
            # let value_res =
            #   let vid = Value.fresh () in
            #   let typ = note in
            #   Il.Ast.(CaseV (mixop, values) $$$ { vid; typ })
            value_res = objects.CaseV.make(values, mixop, self.typ)
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
            value_res = objects.TextV(value_l.value + value_r.value, self.typ)
        #     | ListV values_l, ListV values_r -> Il.Ast.ListV (values_l @ values_r)
        elif isinstance(value_l, objects.ListV) and isinstance(value_r, objects.ListV):
            if not value_l._get_size_list():
                value_res = value_r
            elif not value_r._get_size_list():
                value_res = value_l
            else:
                value_res = objects.ListV.make(value_l.get_list() + value_r.get_list(), self.typ)
        else:
            assert 0, "concatenation expects either two texts or two lists"
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
        value_res = objects.ListV.make([value_h] + values_t, self.typ)
        return ctx, value_res
        # in
        # Ctx.add_node ctx value_res;
        # (ctx, value_res)

class __extend__(p4specast.LenE):
    def eval_exp(self, ctx):
        # let ctx, value = eval_exp ctx exp in
        ctx, value = eval_exp(ctx, self.lst)
        # let len = value |> Value.get_list |> List.length |> Bigint.of_int in
        value = integers.Integer.fromint(value.get_list_len())
        # let value_res =
        #   let vid = Value.fresh () in
        #   let typ = note in
        #   Il.Ast.(NumV (`Nat len) $$$ { vid; typ })
        value_res = objects.NumV.make(value, p4specast.NatT.INSTANCE, typ=self.typ)
        # in
        # Ctx.add_node ctx value_res;
        # Ctx.add_edge ctx value_res value (Dep.Edges.Op LenOp);
        # (ctx, value_res)
        return ctx, value_res

class __extend__(p4specast.SliceE):
    def eval_exp(self, ctx):
        # let ctx, value_b = eval_exp ctx exp_b in
        ctx, value_b = eval_exp(ctx, self.lst)
        # let values = Value.get_list value_b in
        values = value_b.get_list()
        # let ctx, value_i = eval_exp ctx exp_i in
        ctx, value_i = eval_exp(ctx, self.start)
        # let idx_l = value_i |> Value.get_num |> Num.to_int |> Bigint.to_int_exn in
        idx_l = value_i.get_num().toint()
        # let ctx, value_n = eval_exp ctx exp_n in
        ctx, value_n = eval_exp(ctx, self.length)
        # let idx_n = value_n |> Value.get_num |> Num.to_int |> Bigint.to_int_exn in
        idx_n = value_n.get_num().toint()
        # let idx_h = idx_l + idx_n in
        idx_h = idx_l + idx_n
        # let values_slice =
        #   List.mapi
        #     (fun idx value ->
        #       if idx_l <= idx && idx < idx_h then Some value else None)
        #     values
        #   |> List.filter_map Fun.id
        assert idx_l >= 0
        assert idx_h >= 0
        values_slice = values[idx_l:idx_h]
        # in
        # let value_res =
        #   let vid = Value.fresh () in
        #   let typ = note in
        #   Il.Ast.(ListV values_slice $$$ { vid; typ })
        if not values_slice:
            return ctx, self.typ.empty_list_value()
        value_res = objects.ListV.make(values_slice, self.typ)
        return ctx, value_res
        # in
        # Ctx.add_node ctx value_res;
        # (ctx, value_res)

@jit.unroll_safe
def eval_access_path(value_b, path):
    # match path.it with
    if isinstance(path, p4specast.RootP):
        # | RootP -> value_b
        return value_b
    elif isinstance(path, p4specast.DotP):
        # | DotP (path, atom) ->
        # let value = eval_access_path value_b path in
        value = eval_access_path(value_b, path.path)
        # let fields = value |> Value.get_struct in
        fields = value.get_struct()
        # fields
        # |> List.map (fun (atom, value) -> (atom.it, value))
        # |> List.assoc atom.it
        return fields.get_field(path.atom)
        # | _ -> failwith "(TODO) access_path"
        raise Exception("(TODO) access_path: field not found")
    else:
        raise Exception("(TODO) access_path")


@jit.unroll_safe
def eval_update_path(ctx, value_b, path, value_n):
    # match path.it with
    if isinstance(path, p4specast.RootP):
        # | RootP -> value_n
        return value_n
    elif isinstance(path, p4specast.DotP):
        # | DotP (path, atom) ->
        # let value = eval_access_path value_b path in
        value = eval_access_path(value_b, path.path)
        # let fields = value |> Value.get_struct in
        value = value.get_struct()
        # let fields =
        #   List.map
        #     (fun (atom_f, value_f) ->
        #       if atom_f.it = atom.it then (atom_f, value_n) else (atom_f, value_f))
        #     fields
        value_struct = value.replace_field(path.atom, value_n)
        # let value =
        #   let vid = Value.fresh () in
        #   let typ = path.note in
        #   Il.Ast.(StructV fields $$$ { vid; typ })
        # Ctx.add_node ctx value;
        # eval_update_path ctx value_b path value
        return eval_update_path(ctx, value_b, path.path, value_struct)
    else:
        raise P4EvaluationError("(TODO eval_update_path)")

class __extend__(p4specast.UpdE):
    def eval_exp(self, ctx):
        #   let ctx, value_b = eval_exp ctx exp_b in
        ctx, value_b = eval_exp(ctx, self.exp)
        #   let ctx, value_f = eval_exp ctx exp_f in
        ctx, value_f = eval_exp(ctx, self.value)
        #   let value_res = eval_update_path ctx value_b path value_f in
        return ctx, eval_update_path(ctx, value_b, self.path, value_f)

def eval_iter_exp_opt(note, ctx, exp, vars):
    #   let ctx_sub_opt = Ctx.sub_opt ctx vars in
    ctx_sub_opt = ctx.sub_opt(vars)
    #   let ctx, value_res =
    #     match ctx_sub_opt with
    #     | Some ctx_sub ->
    if ctx_sub_opt is not None:
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
        value_res = note.make_opt_value(value)
        return ctx, value_res
    #     | None ->
    else:
    #         let value_res =
    #           let vid = Value.fresh () in
    #           let typ = note in
    #           Il.Ast.(OptV None $$$ { vid; typ })
        value_res = note.opt_none_value()
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
    ctxs_sub = ctx.sub_list(_make_varlist(vars))
    if ctxs_sub.length == 0:
        value_res = note.empty_list_value()
    elif ctxs_sub.length == 1:
        ctx_sub = next(ctxs_sub)
        ctx_sub, value = eval_exp(ctx_sub, exp)
        ctx = ctx.commit(ctx_sub)
        value_res = objects.ListV.make1(value, note)
    else:
        ctx, values = _eval_iter_exp_list(ctx, exp, ctxs_sub)
        value_res = objects.ListV.make(values, note)
    # in
    # let value_res =
    #   let vid = Value.fresh () in
    #   let typ = note in
    #   Il.Ast.(ListV values $$$ { vid; typ })
    # in
    # Ctx.add_node ctx value_res;
    # List.iter
    #   (fun (id, _typ, iters) ->
    #     let value_sub = Ctx.find_value Local ctx (id, iters @ [ Il.Ast.List ]) in
    #     Ctx.add_edge ctx value_res value_sub Dep.Edges.Iter)
    #   vars;
    # (ctx, value_res)
    return ctx, value_res

def get_printable_location(exp, varlist):
    return "eval_iter_exp_list %s %s" % (exp.tostring(), varlist.tostring())


jitdriver_eval_iter_exp_list = jit.JitDriver(
    reds='auto', greens=['exp', 'varlist'],
    should_unroll_one_iteration = lambda exp, varlist: True,
    name='eval_iter_exp_list', get_printable_location=get_printable_location)


def _eval_iter_exp_list(ctx, exp, ctxs_sub):
    # let ctx, values =
    values = [None] * ctxs_sub.length
    i = 0
    for ctx_sub in ctxs_sub:
        jitdriver_eval_iter_exp_list.jit_merge_point(exp=exp, varlist=ctxs_sub.varlist)
        #   List.fold_left
        #     (fun (ctx, values) ctx_sub ->
        #       let ctx_sub, value = eval_exp ctx_sub exp in
        ctx_sub, value = eval_exp(ctx_sub, exp)
        #       let ctx = Ctx.commit ctx ctx_sub in
        ctx = ctx.commit(ctx_sub)
        #       (ctx, values @ [ value ]))
        #     (ctx, []) ctxs_sub
        values[i] = value
        i += 1
    return ctx, values

class __extend__(p4specast.IterE):
    def eval_exp(self, ctx):
        # let iter, vars = iterexp in
        # match iter with
        if isinstance(self.iter, p4specast.Opt):
            # | Opt -> eval_iter_exp_opt note ctx exp vars
            return eval_iter_exp_opt(self.typ, ctx, self.exp, self.varlist)
        if isinstance(self.iter, p4specast.List):
            # | List -> eval_iter_exp_list note ctx exp vars
            if self.is_simple_list_expr():
                exp = self.exp
                assert isinstance(exp, p4specast.VarE)
                return ctx, ctx.find_value_local(exp.id, p4specast.IterList.EMPTY.append_list())
            return eval_iter_exp_list(self.typ, ctx, self.exp, self.varlist)
        else:
            assert False, "Unknown iter kind: %s" % iter

class __extend__(p4specast.IdxE):
    def eval_exp(self, ctx):
        #   Ctx.t * value =
        # let ctx, value_b = eval_exp ctx exp_b in
        ctx, value_b = eval_exp(ctx, self.lst)
        # let ctx, value_i = eval_exp ctx exp_i in
        ctx, value_i = eval_exp(ctx, self.idx)
        # let values = Value.get_list value_b in
        values = value_b.get_list()
        # let idx = value_i |> Value.get_num |> Num.to_int |> Bigint.to_int_exn in
        idx = value_i.get_num().toint()
        # let value_res = List.nth values idx in
        value_res = values[idx]
        # (ctx, value_res)
        return ctx, value_res

class CtxTup(objects.SubBase):
    def __init__(self, ctx, value):
        self.ctx = ctx
        self.value = value

@objectmodel.always_inline
def pack_if_ctx_different(ctx, value, ctx_orig=None):
    if ctx is ctx_orig:
        return value
    return CtxTup(ctx, value)

@objectmodel.always_inline
def recreate_tuple(tup_or_value, ctx):
    if isinstance(tup_or_value, CtxTup):
        return tup_or_value.ctx, tup_or_value.value
    assert isinstance(tup_or_value, objects.BaseV)
    return ctx, tup_or_value

@objectmodel.always_inline
def eval_exp(ctx, exp):
    return recreate_tuple(exp.tuplifying_eval_exp(ctx), ctx)

def _patch_exp_subcls(cls):
    def tuplifying_eval_exp(self, ctx_orig):
        ctx, value = func(self, ctx_orig)
        return pack_if_ctx_different(ctx, value, ctx_orig)
    func = cls.eval_exp.im_func
    objectmodel.always_inline(func)
    func.func_name += "_" + cls.__name__
    tuplifying_eval_exp.func_name += "_" + cls.__name__
    cls.tuplifying_eval_exp = tuplifying_eval_exp

for cls in p4specast.Exp.__subclasses__():
    _patch_exp_subcls(cls)
del cls


# ____________________________________________________________

@jit.unroll_safe
def subtyp(ctx, typ, value):
    # INCOMPLETE
    # match typ.it with
    # | NumT `NatT -> (
    #     match value.it with
    #     | NumV (`Nat _) -> true
    #     | NumV (`Int i) -> Bigint.(i >= zero)
    #     | _ -> assert false)
    jit.promote(typ)
    if isinstance(typ, p4specast.NumT) and isinstance(typ.typ, p4specast.NatT):
        assert isinstance(value, objects.NumV)
        if value.get_what() == p4specast.NatT.INSTANCE:
            return True
        elif value.get_what() == p4specast.IntT.INSTANCE:
            return value.value.int_ge(0)
        else:
            assert 0
    # | VarT (tid, targs) -> (
    if isinstance(typ, p4specast.VarT):
    #     let tparams, deftyp = Ctx.find_typdef Local ctx tid in
        tparams, deftyp = ctx.find_typdef_local(typ.id, typ)
    #     let theta = List.combine tparams targs |> TIdMap.of_list in
        assert tparams == []
        assert typ.targs == []
        if isinstance(deftyp, p4specast.PlainT):
            #import pdb;pdb.set_trace()
            raise P4EvaluationError("TODO subtyp")
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
    #import pdb;pdb.set_trace()
    raise P4EvaluationError("TODO subtyp")

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
    if (isinstance(typ, p4specast.NumT) and
            isinstance(typ.typ, p4specast.NatT)):
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
        assert isinstance(value, objects.NumV)
        if value.get_what() == p4specast.NatT.INSTANCE:
            return ctx, value
        elif value.get_what() == p4specast.IntT.INSTANCE:
            assert value.value.int_ge(0)
            return ctx, objects.NumV.make(value.value, p4specast.NatT.INSTANCE, typ=typ)
        else:
            assert 0
    # | VarT (tid, targs) -> (
    if isinstance(typ, p4specast.VarT):
        tparams, deftyp = ctx.find_typdef_local(typ.id, typ)
        assert tparams == []
    #     let tparams, deftyp = Ctx.find_typdef Local ctx tid in
    #     let theta = List.combine tparams targs |> TIdMap.of_list in
    #     match deftyp.it with
    #     | PlainT typ ->
        if isinstance(deftyp, p4specast.PlainT):
            #import pdb;pdb.set_trace()
            raise P4CastError("TODO downcast")
    #         let typ = Typ.subst_typ theta typ in
    #         downcast ctx typ value
    #     | _ -> (ctx, value))
        else:
            return ctx, value
    # | TupleT typs -> (
    if isinstance(typ, p4specast.TupleT):
        #import pdb;pdb.set_trace()
        raise P4CastError("TODO downcast")
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
    from rpyp4sp.type_helpers import subst_typ
    # INCOMPLETE
    #   match typ.it with
    #   | NumT `IntT -> (
    if isinstance(typ, p4specast.NumT) and isinstance(typ.typ, p4specast.IntT):
    #       match value.it with
        if isinstance(value, objects.NumV) and value.get_what() == p4specast.NatT.INSTANCE:
    #       | NumV (`Nat n) ->
    #           let value_res =
    #             let vid = Value.fresh () in
    #             let typ = typ.it in
    #             Il.Ast.(NumV (`Int n) $$$ { vid; typ })
            value_res = objects.NumV.make(value.get_num(), p4specast.IntT.INSTANCE, typ=typ)
            return ctx, value_res
    #           in
    #           Ctx.add_node ctx value_res;
    #           Ctx.add_edge ctx value_res value (Dep.Edges.Op (CastOp typ));
    #           (ctx, value_res)
    #       | NumV (`Int _) -> (ctx, value)
    #       | _ -> assert false)
    #   | VarT (tid, targs) -> (
    if isinstance(typ, p4specast.VarT):
    #       let tparams, deftyp = Ctx.find_typdef Local ctx tid in
        tparams, deftyp = ctx.find_typdef_local(typ.id, typ)
    #       let theta = List.combine tparams targs |> TIdMap.of_list in
    #       match deftyp.it with
        if isinstance(deftyp, p4specast.PlainT):
            theta = {}
            if tparams:
                raise P4CastError("TODO upcast")
            # let typ = Typ.subst_typ theta typ in
            # upcast ctx typ value
            return upcast(ctx, subst_typ(theta, deftyp.typ), value)
        else:
            return ctx, value
    #       | PlainT typ ->
    #           let typ = Typ.subst_typ theta typ in
    #           upcast ctx typ value
    #       | _ -> (ctx, value))
    #   | TupleT typs -> (
    if isinstance(typ, p4specast.TupleT):
        #import pdb;pdb.set_trace()
        raise P4CastError("TODO upcast")
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
    return ctx, value


@jit.elidable_promote('0,1')
def mixop_eq(a, b):
    return a.tostring() == b.tostring()
