from rpyp4sp import p4specast, objects
from rpyp4sp.error import P4NotImplementedError, P4BuiltinError

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
        raise P4BuiltinError("Unknown built-in function: %s" % name.value)
    func = all_builtins[name.value]
    return func(ctx, name, targs, values_input)

@register_builtin("sum")
def nats_sum(ctx, name, targs, values_input):
    raise P4NotImplementedError("nats_sum is not implemented yet")

@register_builtin("max")
def nats_max(ctx, name, targs, values_input):
    raise P4NotImplementedError("nats_max is not implemented yet")

@register_builtin("min")
def nats_min(ctx, name, targs, values_input):
    raise P4NotImplementedError("nats_min is not implemented yet")

@register_builtin("int_to_text")
def texts_int_to_text(ctx, name, targs, values_input):
    int_value, = values_input
    return objects.TextV(int_value.get_num().str(), typ=p4specast.TextT())

@register_builtin("strip_prefix")
def texts_strip_prefix(ctx, name, targs, values_input):
    raise P4NotImplementedError("texts_strip_prefix is not implemented yet")

@register_builtin("strip_suffix")
def texts_strip_suffix(ctx, name, targs, values_input):
    raise P4NotImplementedError("texts_strip_suffix is not implemented yet")

@register_builtin("rev_")
def lists_rev_(ctx, name, targs, values_input):
    value, = values_input
    lst = value.get_list()
    if len(lst) <= 1:
        return value
    lst = lst[:]
    lst.reverse()
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
    raise P4NotImplementedError("lists_partition_ is not implemented yet")

@register_builtin("assoc_")
def lists_assoc_(ctx, name, targs, values_input):
    typ_key, typ_value = targs
    value, value_list = values_input
    res_value = None
    for tup in value_list.get_list():
        assert isinstance(tup, objects.TupleV)
        if tup.elements[0].eq(value):
            res_value = tup.elements[1]
            break
    return objects.OptV(res_value, typ=p4specast.IterT(typ_value, p4specast.Opt()))

# ________________________________________________________________
# sets

set_id = p4specast.Id('set', p4specast.NO_REGION)

def _extract_set_elems(set_value):
    assert isinstance(set_value, objects.CaseV)
    assert set_value.mixop.eq(map_mixop)
    assert len(set_value.values) == 1
    lst_value, = set_value.values
    assert isinstance(lst_value, objects.ListV)
    return lst_value.get_list()

def _wrap_set_elems(elems, set_value_for_types):
    assert isinstance(set_value_for_types, objects.CaseV)
    lst_value = objects.ListV(elems, typ=set_value_for_types.values[0].typ)
    return objects.CaseV(set_value_for_types.mixop, [lst_value], typ=set_value_for_types.typ)

@register_builtin("intersect_set")
def sets_intersect_set(ctx, name, targs, values_input):
    raise P4NotImplementedError("sets_intersect_set is not implemented yet")

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
    element_typ, = targs
    if not sets_l:
        return objects.CaseV(
            map_mixop,
            [objects.ListV(
                [],
                typ=p4specast.IterT(element_typ, p4specast.List()))],
            typ=p4specast.VarT(set_id, targs))
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
    raise P4NotImplementedError("sets_sub_set is not implemented yet")

@register_builtin("eq_set")
def sets_eq_set(ctx, name, targs, values_input):
    set_l, set_r = values_input
    elems_l = _extract_set_elems(set_l)
    elems_r = _extract_set_elems(set_r)
    if len(elems_l) != len(elems_r):
        return objects.BoolV(False, typ=p4specast.BoolT())
    for el in elems_l:
        for el2 in elems_r:
            if el.eq(el2):
                break
        else:
            return objects.BoolV(False, typ=p4specast.BoolT())
    return objects.BoolV(True, typ=p4specast.BoolT())

# _________________________________________________________________

map_mixop = p4specast.MixOp(
    [[p4specast.AtomT('{', p4specast.NO_REGION)],
     [p4specast.AtomT('}', p4specast.NO_REGION)]])
arrow_mixop = p4specast.MixOp(
    [[],
     [p4specast.AtomT('->', p4specast.NO_REGION)],
     []])
map_id = p4specast.Id('map', p4specast.NO_REGION)
pair_id = p4specast.Id('pair', p4specast.NO_REGION)

def _extract_map_content(map_value):
    assert isinstance(map_value, objects.CaseV)
    assert map_value.mixop.eq(map_mixop)
    content, = map_value.values
    assert isinstance(content, objects.ListV)
    return content.elements

def _extract_map_item(el):
    assert isinstance(el, objects.CaseV)
    assert el.mixop.eq(arrow_mixop)
    key, value = el.values
    return key, value

def _build_map_item(key_value, value_value, key_typ, value_typ):
    pairtyp = p4specast.VarT(pair_id, [key_typ, value_typ])
    return objects.CaseV(arrow_mixop, [key_value, value_value], typ=pairtyp)

def _find_map(map_value, key_value):
    content = _extract_map_content(map_value)
    found_value = None
    for el in content:
        key, value = _extract_map_item(el)
        if key.eq(key_value):
            found_value = value
            break
    return found_value

@register_builtin("find_map")
def maps_find_map(ctx, name, targs, values_input):
    key_typ, value_typ = targs
    map_value, key_value = values_input
    found_value = _find_map(map_value, key_value)
    typ = p4specast.IterT(key_typ, p4specast.Opt())
    typ.region = p4specast.NO_REGION
    return objects.OptV(found_value, typ=typ)


@register_builtin("find_maps")
def maps_find_maps(ctx, name, targs, values_input):
    # look through many maps, return first result
    key_typ, value_typ = targs
    list_maps_value, key_value = values_input
    assert isinstance(list_maps_value, objects.ListV)
    res_value = None
    for map_value in list_maps_value.elements:
        res_value = _find_map(map_value, key_value)
        if res_value is not None:
            break
    typ = p4specast.IterT(key_typ, p4specast.Opt())
    typ.region = p4specast.NO_REGION
    return objects.OptV(res_value, typ=typ)

@register_builtin("add_map")
def maps_add_map(ctx, name, targs, values_input):
    map_value, key_value, value_value = values_input
    key_typ, value_typ = targs
    content = _extract_map_content(map_value)
    res = []
    index = 0
    new_pair = _build_map_item(key_value, value_value, key_typ, value_typ)
    for index, el in enumerate(content):
        curr_key_value, value = _extract_map_item(el)
        cmp = curr_key_value.compare(key_value)
        if cmp == -1:
            res.append(el)
        elif cmp == 0:
            res.append(new_pair)
            res.extend(content[index + 1:])
            break

        elif cmp == 1:
            res.append(new_pair)
            res.extend(content[index:])
            break
        else:
            assert 0, 'unreachable'
    else:
        res.append(new_pair)
    list_value = objects.ListV(res, typ=p4specast.IterT(new_pair.typ, p4specast.List()))
    return objects.CaseV(map_mixop, [list_value], typ=p4specast.VarT(map_id, targs))


@register_builtin("adds_map")
def maps_adds_map(ctx, name, targs, values_input):
    value_map, value_key_list, value_value_list = values_input
    keys = value_key_list.get_list()
    values = value_value_list.get_list()
    if len(keys) != len(values):
        raise P4BuiltinError("adds_map: list of keys and list of values must have the same length")
    for index, key_value in enumerate(keys):
        value_value = values[index]
        value_map = maps_add_map(ctx, None, targs, [value_map, key_value, value_value])
    return value_map


@register_builtin("update_map")
def maps_update_map(ctx, name, targs, values_input):
    return maps_add_map(ctx, name, targs, values_input)

class CounterHolder(object):
    def __init__(self):
        self.counter = 0

HOLDER = CounterHolder()

@register_builtin("fresh_tid")
def fresh_fresh_tid(ctx, name, targs, values_input):
    assert targs == []
    assert values_input == []
    # let tid = "FRESH__" ^ string_of_int !ctr in
    tid = "FRESH__%s" % HOLDER.counter
    # ctr := !ctr + 1;
    HOLDER.counter += 1
    # let value =
    #   let vid = Value.fresh () in
    #   let typ = Il.Ast.VarT ("tid" $ no_region, []) in
    #   TextV tid $$$ { vid; typ }
    return objects.TextV(tid,
                         typ=p4specast.VarT(p4specast.Id('tid', p4specast.NO_REGION), []))
    # in
    # Ctx.add_node ctx value;
    # value

def _integer_to_value(integer):
    # type (integers.Integer) -> objects.NumV
    return objects.NumV(integer, 'Int', typ=p4specast.NumT(p4specast.IntT()))


@register_builtin("shl")
def numerics_shl(ctx, name, targs, values_input):
    left, right = values_input
    return _integer_to_value(left.get_num().lshift(right.get_num().toint()))

@register_builtin("shr")
def numerics_shr(ctx, name, targs, values_input):
    left, right = values_input
    return _integer_to_value(left.get_num().rshift(right.get_num().toint()))

@register_builtin("shr_arith")
def numerics_shr_arith(ctx, name, targs, values_input):
    raise P4NotImplementedError("numerics_shr_arith is not implemented yet")

@register_builtin("pow2")
def numerics_pow2(ctx, name, targs, values_input):
    raise P4NotImplementedError("numerics_pow2 is not implemented yet")

@register_builtin("to_int")
def numerics_to_int(ctx, name, targs, values_input):
    raise P4NotImplementedError("numerics_to_int is not implemented yet")

@register_builtin("to_bitstr")
def numerics_to_bitstr(ctx, name, targs, values_input):
    width, num = values_input
    width_num = width.get_num()
    num_num = num.get_num()
    if not (0 <= num_num.toint() < (1 << width_num.toint())):
        raise P4BuiltinError("TODO: handle numeric bounds check failure for width %s, num %s" % (width_num.toint(), num_num.toint()))
    return num

@register_builtin("bneg")
def numerics_bneg(ctx, name, targs, values_input):
    raise P4NotImplementedError("numerics_bneg is not implemented yet")

@register_builtin("band")
def numerics_band(ctx, name, targs, values_input):
    raise P4NotImplementedError("numerics_band is not implemented yet")

@register_builtin("bxor")
def numerics_bxor(ctx, name, targs, values_input):
    raise P4NotImplementedError("numerics_bxor is not implemented yet")

@register_builtin("bor")
def numerics_bor(ctx, name, targs, values_input):
    raise P4NotImplementedError("numerics_bor is not implemented yet")

@register_builtin("bitacc")
def numerics_bitacc(ctx, name, targs, values_input):
    raise P4NotImplementedError("numerics_bitacc is not implemented yet")
