from rpython.rlib import jit
from rpyp4sp import p4specast, objects, integers
from rpyp4sp.error import P4NotImplementedError, P4BuiltinError

all_builtins = {}

def register_builtin(name, requires_ctx=False):
    def decorator(func):
        all_builtins[name] = func, requires_ctx
        return func
    return decorator

@jit.elidable
def is_builtin(name):
    return name in all_builtins

@jit.elidable
def _get_function(name):
    return all_builtins.get(name, (None, False))

def invoke(ctx, name, targs, values_input):
    if not is_builtin(name.value):
        raise P4BuiltinError("Unknown built-in function: %s" % name.value)
    jit.jit_debug(name.value)
    func, requires_ctx = _get_function(name.value)
    if not requires_ctx:
        return func(targs, values_input)
    return func(ctx, targs, values_input)

@register_builtin("sum")
def nats_sum(targs, values_input):
    # (* dec $sum(nat* ) : nat *)

    # let sum (ctx : Ctx.t) (at : region) (targs : targ list)
    #     (values_input : value list) : value =
    #   Extract.zero at targs;
    #   let values =
    #     Extract.one at values_input |> Value.get_list |> List.map bigint_of_value
    #   in
    #   let sum = List.fold_left Bigint.( + ) Bigint.zero values in
    #   value_of_bigint ctx sum

    # Extract.one at values_input
    list_value, = values_input

    # Value.get_list |> List.map bigint_of_value
    values = list_value.get_list()

    # let sum = List.fold_left Bigint.( + ) Bigint.zero values
    sum_result = integers.Integer.fromint(0)
    for value in values:
        sum_result = sum_result.add(value.get_num())

    # value_of_bigint ctx sum
    return objects.NumV.make(sum_result, p4specast.NatT.INSTANCE, p4specast.NumT.NAT)

@register_builtin("max")
def nats_max(targs, values_input):
    # (* dec $max(nat* ) : nat *)
    list_value, = values_input
    values = list_value.get_list()
    if not values:
        raise P4BuiltinError("max: empty list")
    max_result = values[0].get_num()
    max_result = _nats_max(values, max_result)
    return objects.NumV.make(max_result, p4specast.NatT.INSTANCE, p4specast.NumT.NAT)

def _nats_max(values, max_result):
    for index in range(1, len(values)):
        value = values[index]
        current = value.get_num()
        if current.gt(max_result):
            max_result = current
    return max_result

@register_builtin("min")
def nats_min(targs, values_input):
    # (* dec $min(nat* ) : nat *)
    list_value, = values_input
    values = list_value.get_list()
    if not values:
        raise P4BuiltinError("min: empty list")
    min_result = values[0].get_num()
    min_result = _nats_min(values, min_result)
    return objects.NumV.make(min_result, p4specast.NatT.INSTANCE, p4specast.NumT.NAT)

def _nats_min(values, min_result):
    for index in range(1, len(values)):
        value = values[index]
        current = value.get_num()
        if current.lt(min_result):
            min_result = current
    return min_result

@register_builtin("int_to_text")
def texts_int_to_text(targs, values_input):
    int_value, = values_input
    return objects.TextV(int_value.get_num().str(), p4specast.TextT.INSTANCE)

@register_builtin("strip_prefix")
def texts_strip_prefix(targs, values_input):
    # Extract.zero at targs;
    # let value_text, value_prefix = Extract.two at values_input in
    # let text = Value.get_text value_text in
    # let prefix = Value.get_text value_prefix in
    # assert (String.starts_with ~prefix text);
    # let text =
    #   String.sub text (String.length prefix)
    #     (String.length text - String.length prefix)
    # in
    # let value =
    #   let vid = Value.fresh () in
    #   let typ = Il.Ast.TextT in
    #   TextV text $$$ { vid; typ }
    # in
    # Ctx.add_node ctx value;
    # value

    value_text, value_prefix = values_input
    text = value_text.get_text()
    prefix = value_prefix.get_text()
    if not text.startswith(prefix):
        raise P4BuiltinError("Text '%s' does not start with prefix '%s'" % (text, prefix))
    stripped_text = text[len(prefix):] if prefix else text
    return objects.TextV(stripped_text, p4specast.TextT.INSTANCE)

@register_builtin("strip_suffix")
def texts_strip_suffix(targs, values_input):
    # Extract.zero at targs;
    # let value_text, value_suffix = Extract.two at values_input in
    # let text = Value.get_text value_text in
    # let suffix = Value.get_text value_suffix in
    # assert (String.ends_with ~suffix text);
    # let text = String.sub text 0 (String.length text - String.length suffix) in
    # let value =
    #   let vid = Value.fresh () in
    #   let typ = Il.Ast.TextT in
    #   TextV text $$$ { vid; typ }
    # in
    # Ctx.add_node ctx value;
    # value
    value_text, value_suffix = values_input
    text = value_text.get_text()
    suffix = value_suffix.get_text()
    if not text.endswith(suffix):
        raise P4BuiltinError("Text '%s' does not end with suffix '%s'" % (text, suffix))
    end = len(text) - len(suffix)
    assert end >= 0
    stripped_text = text[:end]
    return objects.TextV(stripped_text, p4specast.TextT.INSTANCE)

@register_builtin("rev_")
def lists_rev_(targs, values_input):
    value, = values_input
    lst = value.get_list()
    if len(lst) <= 1:
        return value
    lst = lst[:]
    lst.reverse()
    return objects.ListV.make(lst, value.get_typ())


@register_builtin("concat_")
def lists_concat_(targs, values_input):
    value, = values_input
    lists = value.get_list()
    res = []
    if lists:
        _lists_concat(lists, res)
    typ = value.get_typ()
    assert isinstance(typ, p4specast.IterT)
    return objects.ListV.make(res[:], typ.typ)

def _lists_concat(lists, res):
    # TODO: unroll sometimes
    for list_value in lists:
        res.extend(list_value.get_list())

@register_builtin("distinct_")
def lists_distinct_(targs, values_input):
    value, = values_input
    lst = value.get_list()
    if len(lst) <= 1:
        return objects.BoolV.TRUE
    result = _lists_distinct(lst)
    return objects.BoolV.make(result, p4specast.BoolT.INSTANCE)

def _lists_distinct(lst):
    # naive quadratic implementation using .eq
    for i in range(len(lst)):
        for j in range(i + 1, len(lst)):
            if lst[i].eq(lst[j]):
                return False
    return True

@register_builtin("partition_")
def lists_partition_(targs, values_input):
    # dec $partition_<X>(X*, nat) : (X*, X* )
    typ, = targs
    value_list, value_len = values_input
    values = value_list.get_list()
    len_num = value_len.get_num().toint()

    assert len_num >= 0
    values_left = values[:len_num]
    values_right = values[len_num:]

    list_typ = typ.list_of()
    value_left = objects.ListV.make(values_left, list_typ)
    value_right = objects.ListV.make(values_right, list_typ)
    tuple_typ = p4specast.TupleT([list_typ, list_typ])
    return objects.TupleV.make2(value_left, value_right, tuple_typ)


@register_builtin("assoc_")
def lists_assoc_(targs, values_input):
    typ_key, typ_value = targs
    value, value_list = values_input
    res_value = None
    for tup in value_list.get_list():
        assert isinstance(tup, objects.TupleV)
        if tup._get_list(0).eq(value):
            res_value = tup._get_list(1)
            break
    return typ_value.opt_of().make_opt_value(res_value)

# ________________________________________________________________
# sets

set_id = p4specast.Id('set', p4specast.NO_REGION)

def _extract_set_elems(set_value):
    assert isinstance(set_value, objects.CaseV)
    assert set_value.mixop.mixop_eq(map_mixop)
    assert set_value._get_size_list() == 1
    lst_value = set_value._get_list(0)
    assert isinstance(lst_value, objects.ListV)
    return lst_value.get_list()

def _wrap_set_elems(elems, set_value_for_types):
    assert isinstance(set_value_for_types, objects.CaseV)
    lst_value = objects.ListV.make(elems, set_value_for_types._get_list(0).get_typ())
    return objects.CaseV.make1(lst_value, set_value_for_types.mixop, set_value_for_types.get_typ())

@register_builtin("intersect_set")
def sets_intersect_set(targs, values_input):
    #let intersect_set (ctx : Ctx.t) (at : region) (targs : targ list)
    #    (values_input : value list) : value =
    #  let typ_key = Extract.one at targs in
    #  let value_set_a, value_set_b = Extract.two at values_input in
    #  let set_a = set_of_value value_set_a in
    #  let set_b = set_of_value value_set_b in
    #  VSet.inter set_a set_b |> value_of_set ctx typ_key
    set_l, set_r = values_input
    elems_l = _extract_set_elems(set_l)
    elems_r = _extract_set_elems(set_r)
    if len(elems_l) == 0 or len(elems_r) == 0:
        res = []
    else:
        res = _intersect_set(elems_l, elems_r)
    return _wrap_set_elems(res, set_l)

def _intersect_set(elems_l, elems_r):
    res = []
    for el in elems_l:
        for el2 in elems_r:
            if el.eq(el2):
                res.append(el)
                break
    return res

def _set_union_elems(elems_l, elems_r):
    res = elems_l[:]
    # add elems_r that are not already in res
    for el in elems_r:
        for el2 in res:
            if el.eq(el2):
                break
        else:
            res.append(el)
    return res[:]

@register_builtin("union_set")
def sets_union_set(targs, values_input):
    set_l, set_r = values_input
    elems_l = _extract_set_elems(set_l)
    elems_r = _extract_set_elems(set_r)
    if len(elems_l) == 0:
        res = elems_r
    elif len(elems_r) == 0:
        res = elems_l
    else:
        res = _set_union_elems(elems_l, elems_r)
    # TODO: I am not sure the order of elements in the result is exactly like in P4-spectec
    return _wrap_set_elems(res, set_l)

@register_builtin("unions_set")
def sets_unions_set(targs, values_input):
    value_list, = values_input
    sets_l = value_list.get_list()
    element_typ, = targs
    if not sets_l:
        return objects.CaseV.make1(
            element_typ.list_of().empty_list_value(),
            map_mixop,
            p4specast.VarT(set_id, targs))
    first = sets_l[0]
    if len(sets_l) == 1:
        return first
    curr = _extract_set_elems(first)
    if len(curr) == 1:
        curr = _set_add_element(_extract_set_elems(sets_l[1]), curr[0])
        startindex = 2
    else:
        startindex = 1
    curr = _unions_set_loop(curr, sets_l, startindex)
    return _wrap_set_elems(curr, first)

def _set_add_element(elems, elem):
    for el in elems:
        if el.eq(elem):
            return elems
    return elems + [elem]

def _unions_set_loop(curr, sets_l, startindex):
    for i in range(startindex, len(sets_l)):
        curr = _set_union_elems(curr, _extract_set_elems(sets_l[i]))
    return curr

@jit.look_inside_iff(lambda elems_l, elems_r: (len(elems_l) <= 1) & (len(elems_r) <= 1))
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
def sets_diff_set(targs, values_input):
    set_l, set_r = values_input
    elems_l = _extract_set_elems(set_l)
    elems_r = _extract_set_elems(set_r)
    if len(elems_l) == 0 or len(elems_r) == 0:
        res = elems_l
    else:
        res = _set_diff_elemens(elems_l, elems_r)
    return _wrap_set_elems(res, set_l)

@register_builtin("sub_set")
def sets_sub_set(targs, values_input):
    #let sub_set (ctx : Ctx.t) (at : region) (targs : targ list)
    #    (values_input : value list) : value =
    #  let _typ_key = Extract.one at targs in
    #  let value_set_a, value_set_b = Extract.two at values_input in
    #  let set_a = set_of_value value_set_a in
    #  let set_b = set_of_value value_set_b in
    #  let value =
    #    let vid = Value.fresh () in
    #    let typ = Il.Ast.BoolT in
    #    BoolV (VSet.subset set_a set_b) $$$ { vid; typ }
    #  in
    #  Ctx.add_node ctx value;
    #  value
    set_l, set_r = values_input
    elems_l = _extract_set_elems(set_l)
    elems_r = _extract_set_elems(set_r)
    # Check if set_l is a subset of set_r (every element in set_l is also in set_r)
    for el in elems_l:
        for el2 in elems_r:
            if el.eq(el2):
                break
        else:
            return objects.BoolV.FALSE
    return objects.BoolV.TRUE

@register_builtin("eq_set")
def sets_eq_set(targs, values_input):
    set_l, set_r = values_input
    elems_l = _extract_set_elems(set_l)
    elems_r = _extract_set_elems(set_r)
    if len(elems_l) != len(elems_r):
        return objects.BoolV.FALSE
    if len(elems_l) == 0:
        result = True
    elif len(elems_l) == 1:
        result = elems_l[0].eq(elems_r[0])
    else:
        result = _sets_eq_set_bool(elems_l, elems_r)
    return objects.BoolV.make(result, p4specast.BoolT.INSTANCE)

def _sets_eq_set_bool(elems_l, elems_r):
    for el in elems_l:
        for el2 in elems_r:
            if el.eq(el2):
                break
        else:
            return False
    return True

# _________________________________________________________________

map_mixop = p4specast.MixOp(
    [p4specast.AtomT('{', p4specast.NO_REGION), None,
     p4specast.AtomT('}', p4specast.NO_REGION)])
arrow_mixop = p4specast.MixOp(
    [None,
     p4specast.AtomT('->', p4specast.NO_REGION),
     None])
map_id = p4specast.Id('map', p4specast.NO_REGION)
pair_id = p4specast.Id('pair', p4specast.NO_REGION)

def _extract_map_content(map_value):
    assert isinstance(map_value, objects.CaseV)
    assert map_value.mixop.mixop_eq(map_mixop)
    assert map_value._get_size_list() == 1
    content = map_value._get_list(0)
    return content.get_list()

def _extract_map_item(el):
    assert isinstance(el, objects.CaseV)
    assert el.mixop.mixop_eq(arrow_mixop)
    assert el._get_size_list() == 2
    key = el._get_list(0)
    value = el._get_list(1)
    return key, value

@jit.elidable
def _make_vart(id, *targs):
    return p4specast.VarT(id, list(targs))

def _build_map_item(key_value, value_value, key_typ, value_typ):
    pairtyp = _make_vart(pair_id, key_typ, value_typ)
    return objects.CaseV.make2(key_value, value_value, arrow_mixop, pairtyp)

def find_map(map_value, key_value):
    content = _extract_map_content(map_value)
    if not content:
        return None
    if len(content) == 1:
        el = content[0]
        key, value = _extract_map_item(el)
        if key.eq(key_value):
            return value
        return None
    return _find_map(key_value, content)

def _find_map(key_value, content):
    for el in content:
        key, value = _extract_map_item(el)
        if key.eq(key_value):
            return value
    return None

@register_builtin("find_map")
def maps_find_map(targs, values_input):
    key_typ, value_typ = targs
    map_value, key_value = values_input
    found_value = find_map(map_value, key_value)
    typ = key_typ.opt_of()
    return typ.make_opt_value(found_value)


@register_builtin("find_maps")
def maps_find_maps(targs, values_input):
    # look through many maps, return first result
    key_typ, value_typ = targs
    list_maps_value, key_value = values_input
    assert isinstance(list_maps_value, objects.ListV)
    res_value = None
    res_value = _maps_find_map(list_maps_value, key_value)
    typ = key_typ.opt_of()
    return typ.make_opt_value(res_value)

@jit.elidable
def _maps_find_map(list_maps_value, key_value):
    for map_value in list_maps_value.get_list():
        res_value = find_map(map_value, key_value)
        if res_value is not None:
            return res_value
    return None

@register_builtin("add_map")
def maps_add_map(targs, values_input):
    map_value, key_value, value_value = values_input
    key_typ, value_typ = targs
    content = _extract_map_content(map_value)
    if not content:
        new_pair = _build_map_item(key_value, value_value, key_typ, value_typ)
        listtyp = new_pair.typ.list_of()
        list_value = objects.ListV.make1(new_pair, listtyp)
    else:
        res = _add_map(key_value, content, value_value, key_typ, value_typ)
        listtyp = jit.promote(res[0].get_typ()).list_of()
        list_value = objects.ListV.make(res, listtyp)
    return objects.CaseV.make1(list_value, map_mixop, _make_vart(map_id, key_typ, value_typ))

def _add_map(key_value, content, value_value, key_typ, value_typ):
    new_pair = _build_map_item(key_value, value_value, key_typ, value_typ)
    listtyp = new_pair.typ.list_of()
    res = []
    index = 0
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
    return res[:]


@register_builtin("adds_map")
def maps_adds_map(targs, values_input):
    value_map, value_key_list, value_value_list = values_input
    keys = value_key_list.get_list()
    values = value_value_list.get_list()
    if len(keys) != len(values):
        raise P4BuiltinError("adds_map: list of keys and list of values must have the same length")
    return _maps_adds_map_loop(targs, value_map, keys, values)

@jit.look_inside_iff(lambda targs, value_map, keys, values: jit.isconstant(len(keys)))
def _maps_adds_map_loop(targs, value_map, keys, values):
    for index, key_value in enumerate(keys):
        value_value = values[index]
        value_map = maps_add_map(targs, [value_map, key_value, value_value])
    return value_map


@register_builtin("update_map")
def maps_update_map(targs, values_input):
    return maps_add_map(targs, values_input)

class CounterHolder(object):
    def __init__(self):
        self.counter = 0

HOLDER = CounterHolder()

TID_VART = p4specast.VarT(p4specast.Id('tid', p4specast.NO_REGION), [])

@register_builtin("fresh_tid")
def fresh_fresh_tid(targs, values_input):
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
                         typ=TID_VART)
    # in
    # Ctx.add_node ctx value;
    # value

def _integer_to_value(integer):
    # type: (integers.Integer) -> objects.NumV
    return objects.NumV.make(integer, p4specast.IntT.INSTANCE, p4specast.NumT.INT)


@register_builtin("shl")
def numerics_shl(targs, values_input):
    left, right = values_input
    return _integer_to_value(left.get_num().lshift(right.get_num().toint()))

@register_builtin("shr")
def numerics_shr(targs, values_input):
    left, right = values_input
    return _integer_to_value(left.get_num().rshift(right.get_num().toint()))

@register_builtin("shr_arith")
def numerics_shr_arith(targs, values_input):
    raise P4NotImplementedError("numerics_shr_arith is not implemented yet")

@register_builtin("pow2")
def numerics_pow2(targs, values_input):
    arg, = values_input
    val = arg.get_num().toint()
    if val < 0:
        raise P4BuiltinError("pow2 argument must not be negative")
    res = integers.Integer.fromint(1).lshift(val)
    return _integer_to_value(res)

@register_builtin("to_int")
def numerics_to_int(targs, values_input):
    width, num = values_input
    width = width.get_num().toint()
    num_num = num.get_num()
    # sign extend num_num
    maxvalue = integers.Integer.fromint(1).lshift(width)
    num_num = num_num.mod(maxvalue) # normalize in range 0..2**width-1
    rightmost_bit = num_num.rshift(width - 1)
    if rightmost_bit.int_eq(0):
        return _integer_to_value(num_num)
    return _integer_to_value(num_num.sub(maxvalue))

@register_builtin("to_bitstr")
def numerics_to_bitstr(targs, values_input):
    width, num = values_input
    width_num = width.get_num()
    num_num = num.get_num()
    maxvalue = integers.Integer.fromint(1).lshift(width_num.toint())
    return _integer_to_value(num_num.mod(maxvalue))

@register_builtin("bneg")
def numerics_bneg(targs, values_input):
    # Extract.zero at targs;
    # let value = Extract.one at values_input in
    # let rawint = bigint_of_value value in
    # Bigint.bit_not rawint |> value_of_bigint
    value, = values_input
    result = value.get_num().invert()
    return _integer_to_value(result)

@register_builtin("band")
def numerics_band(targs, values_input):
    left, right = values_input
    return _integer_to_value(left.get_num().and_(right.get_num()))

@register_builtin("bxor")
def numerics_bxor(targs, values_input):
    left, right = values_input
    return _integer_to_value(left.get_num().xor(right.get_num()))

@register_builtin("bor")
def numerics_bor(targs, values_input):
    left, right = values_input
    return _integer_to_value(left.get_num().or_(right.get_num()))

@register_builtin("bitacc")
def numerics_bitacc(targs, values_input):
    #(* dec $bitacc(int, int, int) : int *)
    #
    #let bitacc' (n : Bigint.t) (m : Bigint.t) (l : Bigint.t) : Bigint.t =
    #  let slice_width = Bigint.(m + one - l) in
    #  if Bigint.(l < zero) then
    #    raise (Invalid_argument "bitslice x[y:z] must have y > z > 0");
    #  let shifted = Bigint.(n asr to_int_exn l) in
    #  let mask = Bigint.(pow2' slice_width - one) in
    #  Bigint.bit_and shifted mask
    #
    #let bitacc (ctx : Ctx.t) (at : region) (targs : targ list)
    #    (values_input : value list) : value =
    #  Extract.zero at targs;
    #  let value_b, value_h, value_l = Extract.three at values_input in
    #  let rawint_b = bigint_of_value value_b in
    #  let rawint_h = bigint_of_value value_h in
    #  let rawint_l = bigint_of_value value_l in
    #  bitacc' rawint_b rawint_h rawint_l |> value_of_bigint ctx

    value_b, value_h, value_l = values_input

    rawint_b = value_b.get_num()  # n
    rawint_h = value_h.get_num()  # m (high bit)
    rawint_l = value_l.get_num()  # l (low bit)

    # let slice_width = Bigint.(m + one - l) in
    slice_width = rawint_h.int_add(1).sub(rawint_l)

    # if Bigint.(l < zero) then raise (Invalid_argument "bitslice x[y:z] must have y > z > 0");
    if rawint_l.int_lt(0):
        raise P4BuiltinError("bitslice x[y:z] must have y > z > 0")

    # let shifted = Bigint.(n asr to_int_exn l) in
    shifted = rawint_b.rshift(rawint_l.toint())

    # let mask = Bigint.(pow2' slice_width - one) in
    mask = integers.Integer.fromint(1).lshift(slice_width.toint()).int_sub(1)

    # Bigint.bit_and shifted mask
    result = shifted.and_(mask)

    return _integer_to_value(result)
