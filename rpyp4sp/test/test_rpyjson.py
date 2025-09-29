import pytest
from rpyp4sp import rpyjson


class TestJsonDumps(object):

    def test_json_primitives(self):
        # Test null
        fragments = []
        rpyjson.json_null.dumps(fragments)
        assert "".join(fragments) == "null"

        # Test true
        fragments = []
        rpyjson.json_true.dumps(fragments)
        assert "".join(fragments) == "true"

        # Test false
        fragments = []
        rpyjson.json_false.dumps(fragments)
        assert "".join(fragments) == "false"

    def test_json_int(self):
        # Test positive int
        fragments = []
        json_int = rpyjson.JsonInt(42)
        json_int.dumps(fragments)
        assert "".join(fragments) == "42"

        # Test negative int
        fragments = []
        json_int = rpyjson.JsonInt(-123)
        json_int.dumps(fragments)
        assert "".join(fragments) == "-123"

        # Test zero
        fragments = []
        json_int = rpyjson.JsonInt(0)
        json_int.dumps(fragments)
        assert "".join(fragments) == "0"

    def test_json_float(self):
        # Test positive float
        fragments = []
        json_float = rpyjson.JsonFloat(3.14)
        json_float.dumps(fragments)
        assert "".join(fragments) == "3.14"

        # Test negative float
        fragments = []
        json_float = rpyjson.JsonFloat(-2.5)
        json_float.dumps(fragments)
        assert "".join(fragments) == "-2.5"

        # Test zero float
        fragments = []
        json_float = rpyjson.JsonFloat(0.0)
        json_float.dumps(fragments)
        assert "".join(fragments) == "0.0"

    def test_json_empty_array(self):
        # Test empty array
        fragments = []
        json_array = rpyjson.JsonArray([])
        json_array.dumps(fragments)
        assert "".join(fragments) == "[]"

    def test_json_array_single_element(self):
        # Test array with single element
        fragments = []
        json_array = rpyjson.JsonArray([rpyjson.JsonInt(42)])
        json_array.dumps(fragments)
        assert "".join(fragments) == "[42]"

    def test_json_array_multiple_elements(self):
        # Test array with multiple elements
        fragments = []
        json_array = rpyjson.JsonArray([
            rpyjson.JsonInt(1),
            rpyjson.json_true,
            rpyjson.json_null,
            rpyjson.JsonFloat(3.14)
        ])
        json_array.dumps(fragments)
        assert "".join(fragments) == "[1, true, null, 3.14]"

    def test_json_empty_object(self):
        # Test empty object
        fragments = []
        json_obj = rpyjson.JsonObject0(rpyjson.ROOT_MAP)
        json_obj.dumps(fragments)
        assert "".join(fragments) == "{}"

    def test_json_object_single_field(self):
        # Test object with single field
        fragments = []
        map_with_key = rpyjson.ROOT_MAP.get_next("name")
        json_obj = rpyjson.JsonObject1(map_with_key, rpyjson.JsonInt(42))
        json_obj.dumps(fragments)
        assert "".join(fragments) == '{"name": 42}'

    def test_json_object_multiple_fields(self):
        # Test object with multiple fields
        fragments = []
        map1 = rpyjson.ROOT_MAP.get_next("age")
        map2 = map1.get_next("active")
        json_obj = rpyjson.JsonObject2(map2, rpyjson.JsonInt(25), rpyjson.json_true)
        json_obj.dumps(fragments)
        # Note: order depends on iteritems() but should be consistent
        result = "".join(fragments)
        assert '{"age": 25' in result
        assert '"active": true' in result
        assert result.startswith("{") and result.endswith("}")

    def test_nested_structures(self):
        # Test nested array and object
        fragments = []

        # Create inner array: [1, 2]
        inner_array = rpyjson.JsonArray([rpyjson.JsonInt(1), rpyjson.JsonInt(2)])

        # Create object with array: {"numbers": [1, 2]}
        map_with_numbers = rpyjson.ROOT_MAP.get_next("numbers")
        json_obj = rpyjson.JsonObject1(map_with_numbers, inner_array)

        json_obj.dumps(fragments)
        assert "".join(fragments) == '{"numbers": [1, 2]}'

    def test_deeply_nested_structure(self):
        # Test deeply nested structure
        fragments = []

        # Build: {"data": {"items": [true, false, null]}}
        inner_array = rpyjson.JsonArray([rpyjson.json_true, rpyjson.json_false, rpyjson.json_null])

        items_map = rpyjson.ROOT_MAP.get_next("items")
        inner_obj = rpyjson.JsonObject1(items_map, inner_array)

        data_map = rpyjson.ROOT_MAP.get_next("data")
        outer_obj = rpyjson.JsonObject1(data_map, inner_obj)

        outer_obj.dumps(fragments)
        assert "".join(fragments) == '{"data": {"items": [true, false, null]}}'

    def test_array_of_objects(self):
        # Test array containing objects
        fragments = []

        # Create two objects: {"id": 1} and {"id": 2}
        id_map = rpyjson.ROOT_MAP.get_next("id")
        obj1 = rpyjson.JsonObject1(id_map, rpyjson.JsonInt(1))
        obj2 = rpyjson.JsonObject1(id_map, rpyjson.JsonInt(2))

        json_array = rpyjson.JsonArray([obj1, obj2])
        json_array.dumps(fragments)
        assert "".join(fragments) == '[{"id": 1}, {"id": 2}]'

    def test_large_array(self):
        # Test array with many elements
        fragments = []
        elements = [rpyjson.JsonInt(i) for i in range(10)]
        json_array = rpyjson.JsonArray(elements)
        json_array.dumps(fragments)
        expected = "[" + ", ".join(str(i) for i in range(10)) + "]"
        assert "".join(fragments) == expected

    def test_object_with_different_value_types(self):
        # Test object with various value types
        fragments = []

        # Build incrementally: {"num": 42, "flag": true, "data": null}
        map1 = rpyjson.ROOT_MAP.get_next("num")
        map2 = map1.get_next("flag")
        map3 = map2.get_next("data")

        json_obj = rpyjson.JsonObject3(
            map3,
            rpyjson.JsonInt(42),     # num
            rpyjson.json_true,       # flag
            rpyjson.json_null        # data
        )

        json_obj.dumps(fragments)
        result = "".join(fragments)
        # Check all key-value pairs are present
        assert '"num": 42' in result
        assert '"flag": true' in result
        assert '"data": null' in result
        assert result.startswith("{") and result.endswith("}")

    def test_json_string_simple(self):
        # Test simple string
        fragments = []
        json_string = rpyjson.JsonString("hello")
        json_string.dumps(fragments)
        assert "".join(fragments) == '"hello"'

    def test_json_string_empty(self):
        # Test empty string
        fragments = []
        json_string = rpyjson.JsonString("")
        json_string.dumps(fragments)
        assert "".join(fragments) == '""'

    def test_json_string_with_quotes(self):
        # Test string with quotes
        fragments = []
        json_string = rpyjson.JsonString('say "hello"')
        json_string.dumps(fragments)
        assert "".join(fragments) == '"say \\"hello\\""'

    def test_json_string_with_backslash(self):
        # Test string with backslash
        fragments = []
        json_string = rpyjson.JsonString("path\\to\\file")
        json_string.dumps(fragments)
        assert "".join(fragments) == '"path\\\\to\\\\file"'

    def test_json_string_with_newlines(self):
        # Test string with newlines and tabs
        fragments = []
        json_string = rpyjson.JsonString("line1\nline2\tindented")
        json_string.dumps(fragments)
        assert "".join(fragments) == '"line1\\nline2\\tindented"'

    def test_json_string_with_control_chars(self):
        # Test string with control characters
        fragments = []
        json_string = rpyjson.JsonString("hello\x01\x1fworld")
        json_string.dumps(fragments)
        assert "".join(fragments) == '"hello\\u0001\\u001fworld"'

    def test_json_string_with_all_escapes(self):
        # Test string with all escape sequences
        fragments = []
        test_string = '"\\\b\f\n\r\t'
        json_string = rpyjson.JsonString(test_string)
        json_string.dumps(fragments)
        assert "".join(fragments) == '"\\"\\\\\\b\\f\\n\\r\\t"'

    def test_object_with_escaped_keys(self):
        # Test object with keys that need escaping
        fragments = []
        map_with_special_key = rpyjson.ROOT_MAP.get_next('key with "quotes"')
        json_obj = rpyjson.JsonObject1(map_with_special_key, rpyjson.JsonInt(42))
        json_obj.dumps(fragments)
        assert "".join(fragments) == '{"key with \\"quotes\\"": 42}'

    def test_roundtrip_simple_structures(self):
        # Test that we can serialize structures that came from parsing
        # Parse a simple structure
        parsed = rpyjson.loads('{"name": "test", "value": 123, "active": true}')

        # Serialize it back
        fragments = []
        parsed.dumps(fragments)
        result = "".join(fragments)

        # Should contain all the key-value pairs
        assert '"name": "test"' in result
        assert '"value": 123' in result
        assert '"active": true' in result
        assert result.startswith("{") and result.endswith("}")

    def test_roundtrip_nested_structures(self):
        # Test roundtrip of nested structures
        parsed = rpyjson.loads('{"data": [1, 2, {"nested": null}]}')

        fragments = []
        parsed.dumps(fragments)
        result = "".join(fragments)

        assert '"data": [1, 2, {"nested": null}]' in result

    def test_dumps_convenience_function(self):
        # Test the module-level dumps() convenience function
        json_obj = rpyjson.JsonArray([
            rpyjson.JsonInt(1),
            rpyjson.JsonString("hello"),
            rpyjson.json_true
        ])

        result = rpyjson.dumps(json_obj)
        assert result == '[1, "hello", true]'

        # Test with object
        map_with_field = rpyjson.ROOT_MAP.get_next("message")
        json_obj = rpyjson.JsonObject1(map_with_field, rpyjson.JsonString("test"))

        result = rpyjson.dumps(json_obj)
        assert result == '{"message": "test"}'