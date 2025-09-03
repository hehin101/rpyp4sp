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
    # let ctx_local = Ctx.localize_inputs ctx_local values_input in
    # let ctx_local = assign_args ctx ctx_local args_input values_input in
    # let ctx_local, sign = eval_instrs ctx_local Cont instrs in
    ctx_local, sign = eval_instrs(ctx, Cont(), func.instrs)
    # let ctx = Ctx.commit ctx ctx_local in


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
    import pdb; pdb.set_trace()
    #   | CaseI (exp, cases, phantom_opt) -> eval_case_instr ctx exp cases phantom_opt
    #   | OtherwiseI instr -> eval_instr ctx instr
    #   | LetI (exp_l, exp_r, iterexps) -> eval_let_instr ctx exp_l exp_r iterexps
    #   | RuleI (id, notexp, iterexps) -> eval_rule_instr ctx id notexp iterexps
    #   | ResultI exps -> eval_result_instr ctx exps
    #   | ReturnI exp -> eval_return_instr ctx exp

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
    import pdb; pdb.set_trace()