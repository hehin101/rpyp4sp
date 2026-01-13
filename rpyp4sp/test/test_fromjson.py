from __future__ import print_function
import os
from rpyp4sp import p4specast, objects
from rpyp4sp.rpyjson import loads, JSONDecoder

def test_jsonparser():
    s = '{"calltype":"function","name":"check_func_name","inputs":[{"it":["TextV","pipe"],"note":{"vid":384,"typ":["VarT",{"it":"id","note":null,"at":{"left":{"file":"","line":0,"column":0},"right":{"file":"","line":0,"column":0}}},[]]},"at":null},{"it":["TextV","pipe"],"note":{"vid":322,"typ":["VarT",{"it":"id","note":null,"at":{"left":{"file":"","line":0,"column":0},"right":{"file":"","line":0,"column":0}}},[]]},"at":null}],"result":{"it":["BoolV",true],"note":{"vid":44492,"typ":["BoolT"]},"at":null}}'

    decoder = JSONDecoder(s)
    try:
        w_res = decoder.decode_any(0)
        i = decoder.skip_whitespace(decoder.pos)
        if i < len(s):
            start = i
            end = len(s) - 1
            assert False, 'extra data'
    finally:
        decoder.close()
    assert w_res.is_object


def test_jsonparser_fast_path_position():
    s = '{"calltype":"function","name":"check_func_name","inputs":[{"it":["TextV","pipe"],"note":{"vid":384,"typ":["VarT",{"it":"id","note":null,"at":{"left":{"file":"","line":0,"column":0},"right":{"file":"","line":0,"column":0}}},[]]},"at":null},{"it":["TextV","pipe"],"note":{"vid":322,"typ":["VarT",{"it":"id","note":null,"at":{"left":{"file":"","line":0,"column":0},"right":{"file":"","line":0,"column":0}}},[]]},"at":null}],"result":{"it":["BoolV",true],"note":{"vid":44492,"typ":["BoolT"]},"at":null}}'
    res = loads(s, force=True)


def test_full_ast_rpython():
    currfile = os.path.abspath(__file__)
    basedir = os.path.dirname(os.path.dirname(os.path.dirname(currfile)))
    fn = os.path.join(basedir, "ast.json")
    with open(fn) as f:
        value = loads(f.read())
    if value.is_object:
        value = value.get_dict_value("ast")
    defs = {}
    for i, d in enumerate(value.value_array()):
        defs[i] = p4specast.Def.fromjson(d)
        repr(defs[i])


def test_example_values_load():
    from rpyp4sp.rpyjson import loads
    import os
    currfile = os.path.abspath(__file__)
    testdir = os.path.dirname(currfile)
    fn = os.path.join(testdir, "example_values.json")
    with open(fn) as f:
        value = loads(f.read())
    res = objects.BaseV.fromjson(value)


def test_fromjson_cache():
    from rpyp4sp.rpyjson import loads

    # Test ID caching
    cache = p4specast.FromjsonCache()

    # Create two identical JSON representations of an ID
    json_str = '{"it": "test_id", "note": null, "at": {"left": {"file": "", "line": 0, "column": 0}, "right": {"file": "", "line": 0, "column": 0}}}'
    value1 = loads(json_str)
    value2 = loads(json_str)

    # Parse the same ID twice with cache
    id1 = p4specast.Id.fromjson(value1, cache)
    id2 = p4specast.Id.fromjson(value2, cache)

    # Should return the same object instance due to caching
    assert id1 is id2
    assert id1.value == "test_id"
    assert len(cache.id_cache) == 1

    # Test with different region - should create new object
    json_str_diff_region = '{"it": "test_id", "note": null, "at": {"left": {"file": "test.py", "line": 1, "column": 5}, "right": {"file": "test.py", "line": 1, "column": 10}}}'
    value3 = loads(json_str_diff_region)
    id3 = p4specast.Id.fromjson(value3, cache)

    # Should be different object because region is different
    assert id3 is not id1
    assert id3.value == "test_id"
    assert len(cache.id_cache) == 1  # Still only one entry because same value overwrites

    # Test without cache - should always create new objects
    id4 = p4specast.Id.fromjson(value1, None)
    id5 = p4specast.Id.fromjson(value1, None)

    assert id4 is not id5
    assert id4.value == id5.value == "test_id"


def test_vart_cache():
    from rpyp4sp.rpyjson import loads

    # Test VarT caching with empty targs
    cache = p4specast.FromjsonCache()

    # Create JSON representation of VarT with empty targs
    json_str = '["VarT", {"it": "test_type", "note": null, "at": {"left": {"file": "", "line": 0, "column": 0}, "right": {"file": "", "line": 0, "column": 0}}}, []]'
    value1 = loads(json_str)
    value2 = loads(json_str)

    # Parse the same VarT twice with cache
    region = p4specast.NO_REGION
    vart1 = p4specast.VarT.fromjson(value1, region, cache)
    vart2 = p4specast.VarT.fromjson(value2, region, cache)

    # Should return the same object instance due to caching (empty targs)
    assert vart1 is vart2
    assert vart1.id.value == "test_type"
    assert len(vart1.targs) == 0
    assert len(cache.vart_cache) == 1

    # Test VarT with non-empty targs - should NOT be cached
    json_str_with_targs = '["VarT", {"it": "test_type", "note": null, "at": {"left": {"file": "", "line": 0, "column": 0}, "right": {"file": "", "line": 0, "column": 0}}}, [["BoolT"]]]'
    value3 = loads(json_str_with_targs)
    value4 = loads(json_str_with_targs)

    vart3 = p4specast.VarT.fromjson(value3, region, cache)
    vart4 = p4specast.VarT.fromjson(value4, region, cache)

    # Should be different objects because targs is not empty
    assert vart3 is not vart4
    assert vart3.id.value == "test_type"
    assert len(vart3.targs) == 1
    assert len(cache.vart_cache) == 1  # Still only one entry (the empty targs one)

    # Test with different region - should create new object even with cache
    different_region = p4specast.Region.line_span("test.py", 5, 1, 10)
    vart7 = p4specast.VarT.fromjson(value1, different_region, cache)

    # Should be different object because region is different
    assert vart7 is not vart1
    assert vart7.id.value == "test_type"
    assert len(cache.vart_cache) == 1  # Still only one entry (the original one)

    # Test without cache - should always create new objects
    vart5 = p4specast.VarT.fromjson(value1, region, None)
    vart6 = p4specast.VarT.fromjson(value1, region, None)

    assert vart5 is not vart6
    assert vart5.id.value == vart6.id.value == "test_type"


def test_group_i():
    from rpyp4sp.rpyjson import loads

    # Test GroupI parsing with id, expressions, and instructions
    cache = p4specast.FromjsonCache()

    # Create JSON representation of GroupI with an id, list of expressions, and list of instructions
    # GroupI structure: ["GroupI", id, [exps], [instrs]]
    json_str = '''
    {
        "it": [
            "GroupI",
            {"it": "test_group", "note": null, "at": {"left": {"file": "", "line": 0, "column": 0}, "right": {"file": "", "line": 0, "column": 0}}},
            [
                {
                    "it": ["BoolE", true],
                    "note": ["BoolT"],
                    "at": {"left": {"file": "", "line": 0, "column": 0}, "right": {"file": "", "line": 0, "column": 0}}
                }
            ],
            [
                {
                    "it": ["ReturnI", {
                        "it": ["BoolE", false],
                        "note": ["BoolT"],
                        "at": {"left": {"file": "", "line": 0, "column": 0}, "right": {"file": "", "line": 0, "column": 0}}
                    }],
                    "note": null,
                    "at": {"left": {"file": "", "line": 0, "column": 0}, "right": {"file": "", "line": 0, "column": 0}}
                }
            ]
        ],
        "note": null,
        "at": {"left": {"file": "", "line": 0, "column": 0}, "right": {"file": "", "line": 0, "column": 0}}
    }
    '''

    value = loads(json_str)
    group_i = p4specast.Instr.fromjson(value, cache)

    # Verify it's a GroupI instance
    assert isinstance(group_i, p4specast.GroupI)

    # Verify the id
    assert isinstance(group_i.id, p4specast.Id)
    assert group_i.id.value == "test_group"

    # Verify the expressions list
    assert len(group_i.exps) == 1
    assert isinstance(group_i.exps[0], p4specast.LiteralE)
    assert group_i.exps[0].value.value == True

    # Verify the instructions list
    assert len(group_i.instrs) == 1
    assert isinstance(group_i.instrs[0], p4specast.ReturnI)
    assert isinstance(group_i.instrs[0].exp, p4specast.LiteralE)
    assert group_i.instrs[0].exp.value.value == False

    # Test with empty expressions and instructions
    json_str_empty = '''
    {
        "it": [
            "GroupI",
            {"it": "empty_group", "note": null, "at": {"left": {"file": "", "line": 0, "column": 0}, "right": {"file": "", "line": 0, "column": 0}}},
            [],
            []
        ],
        "note": null,
        "at": {"left": {"file": "", "line": 0, "column": 0}, "right": {"file": "", "line": 0, "column": 0}}
    }
    '''

    value_empty = loads(json_str_empty)
    group_i_empty = p4specast.Instr.fromjson(value_empty, cache)

    assert isinstance(group_i_empty, p4specast.GroupI)
    assert group_i_empty.id.value == "empty_group"
    assert len(group_i_empty.exps) == 0
    assert len(group_i_empty.instrs) == 0

