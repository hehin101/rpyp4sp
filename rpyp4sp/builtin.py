from rpyp4sp import p4specast, objects

all_builtins = {}

def register_builtin(name):
    def decorator(func):
        all_builtins[name] = func
        return func
    return decorator


def is_builtin(name):
    return name in all_builtins

def invoke(ctx, name, targs, values_input):
    if not is_builtin(name.value):
        raise ValueError("Unknown built-in function: %s" % name.value)
    func = all_builtins[name.value]
    return func(ctx, name, targs, values_input)

@register_builtin("sum")
def nats_sum(ctx, name, targs, values_input):
    import pdb; pdb.set_trace()
    raise NotImplementedError("nats_sum is not implemented yet")

@register_builtin("max")
def nats_max(ctx, name, targs, values_input):
    import pdb; pdb.set_trace()
    raise NotImplementedError("nats_max is not implemented yet")

@register_builtin("min")
def nats_min(ctx, name, targs, values_input):
    raise NotImplementedError("nats_min is not implemented yet")

@register_builtin("int_to_text")
def texts_int_to_text(ctx, name, targs, values_input):
    raise NotImplementedError("texts_int_to_text is not implemented yet")

@register_builtin("strip_prefix")
def texts_strip_prefix(ctx, name, targs, values_input):
    raise NotImplementedError("texts_strip_prefix is not implemented yet")

@register_builtin("strip_suffix")
def texts_strip_suffix(ctx, name, targs, values_input):
    raise NotImplementedError("texts_strip_suffix is not implemented yet")

@register_builtin("rev_")
def lists_rev_(ctx, name, targs, values_input):
    value, = values_input
    lst = value.get_list()
    if len(lst) <= 1:
        return value
    lst = lst[::-1]
    return objects.ListV(lst, typ=value.typ)


@register_builtin("concat_")
def lists_concat_(ctx, name, targs, values_input):
    value, = values_input
    lists = value.get_list()
    res = []
    for list_value in lists:
        res.extend(list_value.get_list())
    typ = value.typ
    assert isinstance(typ, p4specast.IterT)
    return objects.ListV(res, typ=typ.typ)

@register_builtin("distinct_")
def lists_distinct_(ctx, name, targs, values_input):
    value, = values_input
    lst = value.get_list()
    if len(lst) <= 1:
        return objects.BoolV(True, typ=p4specast.BoolT())
    # naive quadratic implementation using .eq
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            if lst[i].eq(lst[j]):
                return objects.BoolV(False, typ=p4specast.BoolT())
    return objects.BoolV(True, typ=p4specast.BoolT())

@register_builtin("partition_")
def lists_partition_(ctx, name, targs, values_input):
    raise NotImplementedError("lists_partition_ is not implemented yet")

@register_builtin("assoc_")
def lists_assoc_(ctx, name, targs, values_input):
    raise NotImplementedError("lists_assoc_ is not implemented yet")

# ________________________________________________________________
# sets

def _extract_set_elems(set_value):
    assert isinstance(set_value, objects.CaseV)
    assert set_value.mixop.eq(map_mixop)
    assert len(set_value.values) == 1
    lst_value, = set_value.values
    assert isinstance(lst_value, objects.ListV)
    return lst_value.get_list()

def _wrap_set_elems(elems, set_value_for_types):
    lst_value = objects.ListV(elems, typ=set_value_for_types.values[0].typ)
    return objects.CaseV(set_value_for_types.mixop, [lst_value], typ=set_value_for_types.typ)

@register_builtin("intersect_set")
def sets_intersect_set(ctx, name, targs, values_input):
    raise NotImplementedError("sets_intersect_set is not implemented yet")

def _set_union_elems(elems_l, elems_r):
    res = []
    for el in elems_l + elems_r:
        for el2 in res:
            if el.eq(el2):
                break
        else:
            res.append(el)
    return res

@register_builtin("union_set")
def sets_union_set(ctx, name, targs, values_input):
    set_l, set_r = values_input
    elems_l = _extract_set_elems(set_l)
    elems_r = _extract_set_elems(set_r)
    res = _set_union_elems(elems_l, elems_r)
    # TODO: I am not sure the order of elements in the result is exactly like in P4-spectec
    return _wrap_set_elems(res, set_l)

@register_builtin("unions_set")
def sets_unions_set(ctx, name, targs, values_input):
    value_list, = values_input
    sets_l = value_list.get_list()
    if not sets_l:
        assert 0, "TODO sets_unions_set empty case, needs complicated targs"
    first = sets_l[0]
    curr = _extract_set_elems(first)
    for i in range(1, len(sets_l)):
        curr = _set_union_elems(curr, _extract_set_elems(sets_l[i]))
    return _wrap_set_elems(curr, first)

def _set_diff_elemens(elems_l, elems_r):
    res = []
    for el in elems_l:
        for el2 in elems_r:
            if el.eq(el2):
                break
        else:
            res.append(el)
    return res


@register_builtin("diff_set")
def sets_diff_set(ctx, name, targs, values_input):
    set_l, set_r = values_input
    elems_l = _extract_set_elems(set_l)
    elems_r = _extract_set_elems(set_r)
    res = _set_diff_elemens(elems_l, elems_r)
    return _wrap_set_elems(res, set_l)

@register_builtin("sub_set")
def sets_sub_set(ctx, name, targs, values_input):
    raise NotImplementedError("sets_sub_set is not implemented yet")

@register_builtin("eq_set")
def sets_eq_set(ctx, name, targs, values_input):
    raise NotImplementedError("sets_eq_set is not implemented yet")

# _________________________________________________________________

map_mixop = p4specast.MixOp(
    [[p4specast.AtomT('{', p4specast.NO_REGION)],
     [p4specast.AtomT('}', p4specast.NO_REGION)]])
arrow_mixop = p4specast.MixOp(
    [[],
     [p4specast.AtomT('->', p4specast.NO_REGION)],
     []])

@register_builtin("find_map")
def maps_find_map(ctx, name, targs, values_input):
    key_typ, value_typ = targs
    map_value, key_value = values_input
    assert map_value.mixop.eq(map_mixop)
    content, = map_value.values
    assert isinstance(content, objects.ListV)
    found_value = None
    for el in content.elements:
        assert isinstance(el, objects.CaseV)
        assert el.mixop.eq(arrow_mixop)
        key, value = el.values
        if key.eq(key_value):
            found_value = value
            break
    typ = p4specast.IterT(key_typ, p4specast.Opt())
    typ.region = p4specast.NO_REGION
    return objects.OptV(found_value, typ=typ)


@register_builtin("find_maps")
def maps_find_maps(ctx, name, targs, values_input):
    raise NotImplementedError("maps_find_maps is not implemented yet")

@register_builtin("add_map")
def maps_add_map(ctx, name, targs, values_input):
    import pdb;pdb.set_trace()
    raise NotImplementedError("maps_add_map is not implemented yet")

@register_builtin("adds_map")
def maps_adds_map(ctx, name, targs, values_input):
    raise NotImplementedError("maps_adds_map is not implemented yet")

@register_builtin("update_map")
def maps_update_map(ctx, name, targs, values_input):
    raise NotImplementedError("maps_update_map is not implemented yet")

@register_builtin("fresh_tid")
def fresh_fresh_tid(ctx, name, targs, values_input):
    raise NotImplementedError("fresh_fresh_tid is not implemented yet")

@register_builtin("shl")
def numerics_shl(ctx, name, targs, values_input):
    raise NotImplementedError("numerics_shl is not implemented yet")

@register_builtin("shr")
def numerics_shr(ctx, name, targs, values_input):
    raise NotImplementedError("numerics_shr is not implemented yet")

@register_builtin("shr_arith")
def numerics_shr_arith(ctx, name, targs, values_input):
    raise NotImplementedError("numerics_shr_arith is not implemented yet")

@register_builtin("pow2")
def numerics_pow2(ctx, name, targs, values_input):
    raise NotImplementedError("numerics_pow2 is not implemented yet")

@register_builtin("to_int")
def numerics_to_int(ctx, name, targs, values_input):
    raise NotImplementedError("numerics_to_int is not implemented yet")

@register_builtin("to_bitstr")
def numerics_to_bitstr(ctx, name, targs, values_input):
    width, num = values_input
    width_num = width.get_num()
    num_num = num.get_num()
    assert 0 <= num_num.toint() < (1 << width_num.toint()) # TODO: handle otherwise
    return num

@register_builtin("bneg")
def numerics_bneg(ctx, name, targs, values_input):
    raise NotImplementedError("numerics_bneg is not implemented yet")

@register_builtin("band")
def numerics_band(ctx, name, targs, values_input):
    raise NotImplementedError("numerics_band is not implemented yet")

@register_builtin("bxor")
def numerics_bxor(ctx, name, targs, values_input):
    raise NotImplementedError("numerics_bxor is not implemented yet")

@register_builtin("bor")
def numerics_bor(ctx, name, targs, values_input):
    raise NotImplementedError("numerics_bor is not implemented yet")

@register_builtin("bitacc")
def numerics_bitacc(ctx, name, targs, values_input):
    raise NotImplementedError("numerics_bitacc is not implemented yet")
