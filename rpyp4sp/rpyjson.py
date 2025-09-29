from rpython.rlib.objectmodel import we_are_translated, compute_hash, newlist_hint
from rpython.rlib.rarithmetic import intmask
from rpython.tool.pairtype import extendabletype

import sys
from rpython.rlib.rstring import StringBuilder
from rpyp4sp.error import P4ParseError, P4NotImplementedError
from rpython.rlib.objectmodel import specialize, always_inline, r_dict
from rpython.rlib import rfloat, rutf8
from rpython.rtyper.lltypesystem import lltype, rffi
from rpython.rlib.rarithmetic import r_uint
from pypy.interpreter.error import oefmt
from pypy.interpreter import unicodehelper


# Union-Object to represent a json structure in a static way
class JsonBase(object):
    __metaclass__ = extendabletype

    is_string = is_int = is_float = is_bool = is_object = is_array = is_null = False

    def __init__(self):
        raise P4NotImplementedError("abstract base class")

    def tostring(self):
        raise P4NotImplementedError("abstract base class")

    def dumps(self, strfragments):
        raise P4NotImplementedError("abstract base class")

    def is_primitive(self):
        return False

    def _unpack_deep(self):
        "NON_RPYTHON"
        assert 0, 'base class'

    def __repr__(self):
        return "<json %r>" % (self._unpack_deep(), )

    def value_array(self):
        raise TypeError

    def value_string(self):
        raise TypeError

    def value_bool(self):
        raise TypeError

    def value_float(self):
        raise TypeError

    def value_int(self):
        raise TypeError

    def get_list_item(self, index):
        if self.is_array and isinstance(index, int):
            assert isinstance(self, JsonArray)
            return self.value[index]
        raise TypeError("Invalid index access %s %s" % (self, index))

    @specialize.arg(1)
    def get_dict_value(self, key):
        if self.is_object:
            assert isinstance(self, JsonObject)
            cache = MapLookupCache.get_cache(key)
            index = cache.get(self.map)
            if index < 0:
                raise KeyError(key)
            return self._get_value(index)
        raise TypeError("Invalid key access %s %s" % (self, key))

    def __iter__(self):
        assert isinstance(self, JsonArray)
        return iter(self.value)

    def unpack(self, n):
        assert isinstance(self, JsonArray)
        assert len(self.value) == n
        return self.value

    def __repr__(self):
        import pdb;pdb.set_trace()


class JsonPrimitive(JsonBase):
    def __init__(self):
        pass

    def is_primitive(self):
        return True

class JsonNull(JsonPrimitive):
    is_null = True

    def tostring(self):
        return "null"

    def dumps(self, strfragments):
        strfragments.append("null")

    def _unpack_deep(self):
        return None

    def __repr__(self):
        return "rpyjson.JsonNull()"

class JsonFalse(JsonPrimitive):
    is_bool = True

    def tostring(self):
        return "false"

    def dumps(self, strfragments):
        strfragments.append("false")

    def value_bool(self):
        return False

    def _unpack_deep(self):
        return False

    def __repr__(self):
        return "rpyjson.JsonFalse()"


class JsonTrue(JsonPrimitive):
    is_bool = True

    def tostring(self):
        return "true"

    def dumps(self, strfragments):
        strfragments.append("true")

    def value_bool(self):
        return True

    def _unpack_deep(self):
        return True

    def __repr__(self):
        return "rpyjson.JsonTrue()"

class JsonInt(JsonPrimitive):
    is_int = True

    def __init__(self, value):
        self.value = value

    def tostring(self):
        return str(self.value)

    def dumps(self, strfragments):
        strfragments.append(str(self.value))

    def _unpack_deep(self):
        return self.value

    def value_int(self):
        return self.value

    def __repr__(self):
        return "rpyjson.JsonInt(%d)" % (self.value,)

class JsonFloat(JsonPrimitive):
    is_float = True

    def __init__(self, value):
        self.value = value

    def tostring(self):
        return str(self.value)

    def dumps(self, strfragments):
        strfragments.append(str(self.value))

    def value_float(self):
        return self.value

    def _unpack_deep(self):
        return self.value

    def __repr__(self):
        return "rpyjson.JsonFloat(%r)" % (self.value,)


class JsonString(JsonPrimitive):
    is_string = True

    def __init__(self, value):
        self.value = value

    def tostring(self):
        # this function should really live in a slightly more accessible place
        from pypy.objspace.std.bytesobject import string_escape_encode
        return string_escape_encode(self.value, '"')

    def dumps(self, strfragments):
        strfragments.append('"')
        # Escape special characters according to JSON spec
        for char in self.value:
            if char == '"':
                strfragments.append('\\"')
            elif char == '\\':
                strfragments.append('\\\\')
            elif char == '\b':
                strfragments.append('\\b')
            elif char == '\f':
                strfragments.append('\\f')
            elif char == '\n':
                strfragments.append('\\n')
            elif char == '\r':
                strfragments.append('\\r')
            elif char == '\t':
                strfragments.append('\\t')
            elif ord(char) < 32:
                # Control characters must be escaped as \uXXXX
                strfragments.append('\\u%04x' % ord(char))
            else:
                strfragments.append(char)
        strfragments.append('"')

    def _unpack_deep(self):
        return self.value

    def value_string(self):
        return self.value

    def __repr__(self):
        return "rpyjson.JsonString(%r)" % (self.value,)

class JsonObject(JsonBase):
    is_object = True

    def __init__(self, map):
        self.map = map
        assert self._num_values() == len(map.attrs)

    @staticmethod
    def make(map, values):
        size = len(map.attrs)
        if not size:
            return JsonObject0(map)
        if size == 1:
            return JsonObject1(map, values[0])
        if size == 2:
            return JsonObject2(map, values[0], values[1])
        if size == 3:
            return JsonObject3(map, values[0], values[1], values[2])
        if size == 4:
            return JsonObject4(map, values[0], values[1], values[2], values[3])
        return JsonObjectGeneral(map, values[:size])

    def _num_values(self):
        raise NotImplementedError('abstract')

    def _get_value(self, i):
        raise NotImplementedError('abstract')

    def tostring(self):
        return "{%s}" % ", ".join(["\"%s\": %s" % (key, self._get_value(index).tostring()) for key, index in self.map.attrs.iteritems()])

    def dumps(self, strfragments):
        strfragments.append("{")
        first = True
        for key, index in self.map.attrs.iteritems():
            if not first:
                strfragments.append(", ")
            first = False
            # Create a temporary JsonString to handle key escaping
            key_string = JsonString(key)
            key_string.dumps(strfragments)
            strfragments.append(": ")
            self._get_value(index).dumps(strfragments)
        strfragments.append("}")

    def _unpack_deep(self):
        result = {}
        for key, index in self.map.attrs.iteritems():
            result[key] = self.values[index]._unpack_deep()
        return result

    def __repr__(self):
        return "rpyjson.JsonObject.make(%r, [%s])" % (
                self.map, ", ".join([repr(self._get_value(i)) for i in range(self._num_values())]))

class JsonObject0(JsonObject):
    def _num_values(self):
        return 0

class JsonObject1(JsonObject):
    def __init__(self, map, val0):
        self.val0 = val0
        JsonObject.__init__(self, map)

    def _num_values(self):
        return 1

    def _get_value(self, i):
        assert i == 0
        return self.val0

class JsonObject2(JsonObject):
    def __init__(self, map, val0, val1):
        self.val0 = val0
        self.val1 = val1
        JsonObject.__init__(self, map)

    def _num_values(self):
        return 2

    def _get_value(self, i):
        if i == 0:
            return self.val0
        else:
            assert i == 1
            return self.val1

class JsonObject3(JsonObject):
    def __init__(self, map, val0, val1, val2):
        self.val0 = val0
        self.val1 = val1
        self.val2 = val2
        JsonObject.__init__(self, map)

    def _num_values(self):
        return 3

    def _get_value(self, i):
        if i == 0:
            return self.val0
        elif i == 1:
            return self.val1
        else:
            assert i == 2
            return self.val2

class JsonObject4(JsonObject):
    def __init__(self, map, val0, val1, val2, val3):
        self.val0 = val0
        self.val1 = val1
        self.val2 = val2
        self.val3 = val3
        JsonObject.__init__(self, map)

    def _num_values(self):
        return 4

    def _get_value(self, i):
        if i == 0:
            return self.val0
        elif i == 1:
            return self.val1
        elif i == 2:
            return self.val2
        else:
            assert i == 3
            return self.val3

class JsonObjectGeneral(JsonObject):
    def __init__(self, map, values):
        self.values = values
        JsonObject.__init__(self, map)

    def _num_values(self):
        return len(self.values)

    def _get_value(self, i):
        return self.values[i]


class JsonArray(JsonBase):
    is_array = True

    def __init__(self, lst):
        self.value = lst

    def tostring(self):
        return "[%s]" % ", ".join([e.tostring() for e in self.value])

    def dumps(self, strfragments):
        strfragments.append("[")
        for i, element in enumerate(self.value):
            if i > 0:
                strfragments.append(", ")
            element.dumps(strfragments)
        strfragments.append("]")

    def _unpack_deep(self):
        return [e._unpack_deep() for e in self.value]

    def value_array(self):
        return self.value

    def __repr__(self):
        return "rpyjson.JsonArray(%r)" % (self.value,)

json_null = JsonNull()

json_true = JsonTrue()

json_false = JsonFalse()

json_empty_string = JsonString('')

OVF_DIGITS = len(str(sys.maxint))

def is_whitespace(ch):
    return ch == ' ' or ch == '\t' or ch == '\r' or ch == '\n'

# precomputing negative powers of 10 is MUCH faster than using e.g. math.pow
# at runtime
NEG_POW_10 = [10.0**-i for i in range(16)]
def neg_pow_10(x, exp):
    if exp >= len(NEG_POW_10):
        return 0.0
    return x * NEG_POW_10[exp]

INTCACHE = [JsonInt(i) for i in range(256)]

class Map(object):
    def __init__(self, newkey, attrs):
        self.newkey = newkey # type: str | None
        self.attrs = attrs # type: dict[str, int]
        self.next_maps = None # type: dict[str, Map] | None
        # arbitrarily have a nextmap_first
        self.nextmap_first = None # type: Map
        self.nextmap_first_key_reprish = None

    def get_next(self, key):
        if self.nextmap_first and key == self.nextmap_first.newkey:
            return self.nextmap_first
        if self.next_maps is not None:
            res = self.next_maps.get(key, None)
            if res is not None:
                return res
        else:
            self.next_maps = {}
        attrs = self.attrs.copy()
        attrs[key] = len(attrs)
        newmap = Map(key, attrs)
        self.next_maps[key] = newmap
        if self.nextmap_first is None:
            self.nextmap_first = newmap
            self.nextmap_first_key_reprish = key + '"'
        return newmap

    def lookup(self, key):
        return self.attrs.get(key, -1)

    def __repr__(self):
        res = ["rpyjson.ROOT_MAP"]
        items = self.attrs.items()
        items.sort(key=lambda el: el[1])
        for key, _ in items:
            res.append(".get_next(%r)" % key)
        return "".join(res)

class MapLookupCache(object):
    caches = {}

    @staticmethod
    @specialize.memo()
    def get_cache(key):
        if key in MapLookupCache.caches:
            return MapLookupCache.caches[key]
        cache = MapLookupCache(key)
        MapLookupCache.caches[key] = cache
        return cache

    def __init__(self, key):
        self.key = key
        self.cached_map = None
        self.cached_index = -2

    def get(self, map):
        if map is self.cached_map:
            return self.cached_index
        res = map.lookup(self.key)
        self.cached_map = map
        self.cached_index = res
        return res

ROOT_MAP = Map(None, {})

# prime the root map with some common transitions
ROOT_MAP.get_next("file").get_next("line").get_next("column")
ROOT_MAP.get_next("it").get_next("node").get_next("at")
ROOT_MAP.get_next("left").get_next("right")
ROOT_MAP.get_next("vid").get_next("typ").get_next("at")


TYPE_UNKNOWN = 0
TYPE_STRING = 1
class JSONDecoder(object):
    w_None = json_null
    w_True = json_true
    w_False = json_false

    def __init__(self, s):
        self.s = s
        # we put our string in a raw buffer so:
        # 1) we automatically get the '\0' sentinel at the end of the string,
        #    which means that we never have to check for the "end of string"
        # 2) we can pass the buffer directly to strtod
        self.ll_chars = rffi.str2charp(s)
        self.end_ptr = lltype.malloc(rffi.CCHARPP.TO, 1, flavor='raw')
        self.pos = 0
        self.cache_keys = {}
        self.scratch_lists = []

        self.LRU_SIZE = 16
        self.str_lru_hashes = [-1] * self.LRU_SIZE
        self.str_lru_jsonstrings = [None] * self.LRU_SIZE
        self.str_lru_index = 0

    def close(self):
        rffi.free_charp(self.ll_chars)
        lltype.free(self.end_ptr, flavor='raw')

    def getslice(self, start, end):
        assert start >= 0
        assert end >= 0
        return self.s[start:end]

    def skip_whitespace(self, i):
        while True:
            ch = self.ll_chars[i]
            if is_whitespace(ch):
                i+=1
            else:
                break
        return i

    @specialize.arg(1)
    def _raise(self, msg, *args):
        raise P4ParseError(msg % args)

    def decode_any(self, i):
        i = self.skip_whitespace(i)
        ch = self.ll_chars[i]
        if ch == '"':
            return self.decode_string(i+1)
        elif ch == '[':
            return self.decode_array(i+1)
        elif ch == '{':
            return self.decode_object(i+1)
        elif ch == 'n':
            return self.decode_null(i+1)
        elif ch == 't':
            return self.decode_true(i+1)
        elif ch == 'f':
            return self.decode_false(i+1)
        elif ch == 'I':
            return self.decode_infinity(i+1)
        elif ch == 'N':
            return self.decode_nan(i+1)
        elif ch == '-':
            if self.ll_chars[i+1] == 'I':
                return self.decode_infinity(i+2, sign=-1)
            return self.decode_numeric(i)
        elif ch.isdigit():
            return self.decode_numeric(i)
        else:
            self._raise("No JSON object could be decoded: unexpected '%s' at char %d",
                        ch, i)

    def decode_null(self, i):
        if (self.ll_chars[i]   == 'u' and
            self.ll_chars[i+1] == 'l' and
            self.ll_chars[i+2] == 'l'):
            self.pos = i+3
            return self.w_None
        self._raise("Error when decoding null at char %d", i)

    def decode_true(self, i):
        if (self.ll_chars[i]   == 'r' and
            self.ll_chars[i+1] == 'u' and
            self.ll_chars[i+2] == 'e'):
            self.pos = i+3
            return self.w_True
        self._raise("Error when decoding true at char %d", i)

    def decode_false(self, i):
        if (self.ll_chars[i]   == 'a' and
            self.ll_chars[i+1] == 'l' and
            self.ll_chars[i+2] == 's' and
            self.ll_chars[i+3] == 'e'):
            self.pos = i+4
            return self.w_False
        self._raise("Error when decoding false at char %d", i)

    def decode_infinity(self, i, sign=1):
        if (self.ll_chars[i]   == 'n' and
            self.ll_chars[i+1] == 'f' and
            self.ll_chars[i+2] == 'i' and
            self.ll_chars[i+3] == 'n' and
            self.ll_chars[i+4] == 'i' and
            self.ll_chars[i+5] == 't' and
            self.ll_chars[i+6] == 'y'):
            self.pos = i+7
            return JsonFloat(rfloat.INFINITY * sign)
        self._raise("Error when decoding Infinity at char %d", i)

    def decode_nan(self, i):
        if (self.ll_chars[i]   == 'a' and
            self.ll_chars[i+1] == 'N'):
            self.pos = i+2
            return JsonFloat(rfloat.NAN)
        self._raise("Error when decoding NaN at char %d", i)

    def decode_numeric(self, i):
        start = i
        i, ovf_maybe, intval = self.parse_integer(i)
        #
        # check for the optional fractional part
        ch = self.ll_chars[i]
        if ch == '.':
            if not self.ll_chars[i+1].isdigit():
                self._raise("Expected digit at char %d", i+1)
            return self.decode_float(start)
        elif ch == 'e' or ch == 'E':
            return self.decode_float(start)
        elif ovf_maybe:
            return self.decode_int_slow(start)

        self.pos = i
        if 0 <= intval < len(INTCACHE):
            return INTCACHE[intval]
        return JsonInt(intval)

    def decode_float(self, i):
        from rpython.rlib import rdtoa
        start = rffi.ptradd(self.ll_chars, i)
        floatval = rdtoa.dg_strtod(start, self.end_ptr)
        diff = rffi.cast(rffi.LONG, self.end_ptr[0]) - rffi.cast(rffi.LONG, start)
        self.pos = i + diff
        return JsonFloat(floatval)

    def decode_float(self, i): # TODO: investigate why dg_strtod is not working
        start = i
        while self.ll_chars[i] in "+-0123456789.eE":
            i += 1
        self.pos = i
        return JsonFloat(float(self.getslice(start, i)))


    def decode_int_slow(self, i):
        raise P4ParseError('int too long at position %s' % i)
        start = i
        if self.ll_chars[i] == '-':
            i += 1
        while self.ll_chars[i].isdigit():
            i += 1
        s = self.getslice(start, i)
        self.pos = i
        return self.space.call_function(self.space.w_int, JsonString(s))

    @always_inline
    def parse_integer(self, i):
        "Parse a decimal number with an optional minus sign"
        sign = 1
        # parse the sign
        if self.ll_chars[i] == '-':
            sign = -1
            i += 1
        elif self.ll_chars[i] == '+':
            i += 1
        #
        if self.ll_chars[i] == '0':
            i += 1
            return i, False, 0

        intval = 0
        start = i
        while True:
            ch = self.ll_chars[i]
            if ch.isdigit():
                intval = intval*10 + ord(ch)-ord('0')
                i += 1
            else:
                break
        count = i - start
        if count == 0:
            self._raise("Expected digit at char %d", i)
        # if the number has more digits than OVF_DIGITS, it might have
        # overflowed
        ovf_maybe = (count >= OVF_DIGITS)
        return i, ovf_maybe, sign * intval

    def decode_array(self, i):
        lst = newlist_hint(4)
        w_list = JsonArray(lst)
        start = i
        i = self.skip_whitespace(start)
        if self.ll_chars[i] == ']':
            self.pos = i+1
            return w_list
        #
        while True:
            w_item = self.decode_any(i)
            i = self.pos
            lst.append(w_item)
            i = self.skip_whitespace(i)
            ch = self.ll_chars[i]
            i += 1
            if ch == ']':
                self.pos = i
                return w_list
            elif ch == ',':
                pass
            elif ch == '\0':
                self._raise("Unterminated array starting at char %d", start)
            else:
                self._raise("Unexpected '%s' when decoding array (char %d)",
                            ch, i-1)

    def decode_object(self, i):
        start = i

        i = self.skip_whitespace(i)
        if self.ll_chars[i] == '}':
            self.pos = i+1
            return JsonObject0(ROOT_MAP)

        curr_map = ROOT_MAP
        if self.scratch_lists:
            values = self.scratch_lists.pop()
        else:
            values = [None] * 4
        values_index = 0
        while True:
            # parse a key: value
            curr_map = self.decode_key(curr_map, i)
            i = self.skip_whitespace(self.pos)
            ch = self.ll_chars[i]
            if ch != ':':
                self._raise("No ':' found at char %d", i)
            i += 1
            i = self.skip_whitespace(i)
            #
            w_value = self.decode_any(i)
            if values_index == len(values):
                values = values + [None] * len(values)
            values[values_index] = w_value
            values_index += 1
            i = self.skip_whitespace(self.pos)
            ch = self.ll_chars[i]
            i += 1
            if ch == '}':
                self.pos = i
                res = JsonObject.make(curr_map, values)
                self.scratch_lists.append(values)
                return res
            elif ch == ',':
                pass
            elif ch == '\0':
                self._raise("Unterminated object starting at char %d", start)
            else:
                self._raise("Unexpected '%s' when decoding object (char %d)",
                            ch, i-1)

    def decode_string(self, i):
        start = i
        bits = 0
        ll_chars = self.ll_chars
        strhash = ord(ll_chars[i]) << 7
        while True:
            # this loop is a fast path for strings which do not contain escape
            # characters
            ch = ll_chars[i]
            i += 1
            bits |= ord(ch)
            if ch == '"':
                self.pos = i
                break
            elif ch == '\\' or ch < '\x20':
                self.pos = i-1
                return self.decode_string_escaped(start)
            strhash = intmask((1000003 * strhash) ^ ord(ll_chars[i]))
        length = i - start - 1
        if length == 0:
            strhash = -1
            return json_empty_string
        else:
            strhash ^= length
            strhash = intmask(strhash)
        index = 0
        for index in range(self.LRU_SIZE):
            if self.str_lru_hashes[index] == strhash:
                break
        else:
            # not found
            return self._create_string_wrapped(start, i - 1, strhash)
        cache_str = self.str_lru_jsonstrings[index]
        cache_str_unwrapped = cache_str.value_string()
        if length == len(cache_str_unwrapped):
            index = start
            for c in cache_str_unwrapped:
                if not ll_chars[index] == c:
                    break
                index += 1
            else:
                return cache_str
        # rare: same hash, different string
        return self._create_string_wrapped(start, i - 1, strhash)


    def _create_string_wrapped(self, start, end, strhash):
        res = JsonString(self.getslice(start, end))
        self.str_lru_hashes[self.str_lru_index] = strhash
        self.str_lru_jsonstrings[self.str_lru_index] = res
        self.str_lru_index = (self.str_lru_index + 1) % self.LRU_SIZE
        return res


    def decode_string_escaped(self, start):
        i = self.pos
        builder = StringBuilder((i - start) * 2) # just an estimate
        assert start >= 0
        assert i >= 0
        builder.append_slice(self.s, start, i)
        while True:
            ch = self.ll_chars[i]
            i += 1
            if ch == '"':
                content_utf8 = builder.build()
                self.pos = i
                return JsonString(content_utf8)
            elif ch == '\\':
                i = self.decode_escape_sequence(i, builder)
            elif ch < '\x20':
                if ch == '\0':
                    self._raise("Unterminated string starting at char %d",
                                start - 1)
                else:
                    self._raise("Invalid control character at char %d", i-1)
            else:
                builder.append(ch)

    def decode_escape_sequence(self, i, builder):
        ch = self.ll_chars[i]
        i += 1
        put = builder.append
        if ch == '\\':  put('\\')
        elif ch == '"': put('"' )
        elif ch == '/': put('/' )
        elif ch == 'b': put('\b')
        elif ch == 'f': put('\f')
        elif ch == 'n': put('\n')
        elif ch == 'r': put('\r')
        elif ch == 't': put('\t')
        elif ch == 'u':
            return self.decode_escape_sequence_unicode(i, builder)
        else:
            self._raise("Invalid \\escape: %s (char %d)", ch, i-1)
        return i

    def decode_escape_sequence_unicode(self, i, builder):
        # at this point we are just after the 'u' of the \u1234 sequence.
        start = i
        i += 4
        hexdigits = self.getslice(start, i)
        try:
            val = int(hexdigits, 16)
            if sys.maxunicode > 65535 and 0xd800 <= val <= 0xdfff:
                # surrogate pair
                if self.ll_chars[i] == '\\' and self.ll_chars[i+1] == 'u':
                    val = self.decode_surrogate_pair(i, val)
                    i += 6
        except ValueError:
            self._raise("Invalid \uXXXX escape (char %d)", i-1)
            return # help the annotator to know that we'll never go beyond
                   # this point
        #
        utf8_ch = rutf8.unichr_as_utf8(r_uint(val), allow_surrogates=True)
        builder.append(utf8_ch)
        return i

    def decode_surrogate_pair(self, i, highsurr):
        """ uppon enter the following must hold:
              chars[i] == "\\" and chars[i+1] == "u"
        """
        i += 2
        hexdigits = self.getslice(i, i+4)
        lowsurr = int(hexdigits, 16) # the possible ValueError is caugth by the caller
        return 0x10000 + (((highsurr - 0xd800) << 10) | (lowsurr - 0xdc00))

    def decode_key(self, curr_map, i):
        """ returns the next map"""
        i = self.skip_whitespace(i)
        ll_chars = self.ll_chars
        ch = ll_chars[i]
        if ch != '"':
            self._raise("Key name must be string at char %d", i)
        i += 1
        nextmap = curr_map.nextmap_first
        if nextmap:
            start = i
            for c in curr_map.nextmap_first_key_reprish:
                if c != ll_chars[start]:
                    break
                start += 1
            else:
                self.pos = start
                return nextmap
        key = self._decode_key(i)
        return curr_map.get_next(key)

    def _decode_key(self, i):
        """ returns an unwrapped key """
        ll_chars = self.ll_chars

        start = i
        bits = 0
        strhash = ord(ll_chars[i]) << 7
        while True:
            ch = ll_chars[i]
            i += 1
            if ch == '"':
                break
            elif ch == '\\' or ch < '\x20':
                self.pos = i-1
                return self.decode_string_escaped(start).value_string()
            strhash = intmask((1000003 * strhash) ^ ord(ll_chars[i]))
            bits |= ord(ch)
        length = i - start - 1
        if length == 0:
            strhash = -1
        else:
            strhash ^= length
            strhash = intmask(strhash)
        self.pos = i

        # check cache first:
        try:
            cache_str = self.cache_keys[strhash]
        except KeyError:
            res = self.getslice(start, start + length)
            self.cache_keys[strhash] = res
            return res
        if length == len(cache_str):
            index = start
            for c in cache_str:
                if not ll_chars[index] == c:
                    break
                index += 1
            else:
                return cache_str
        # collision, hopefully rare
        return self.getslice(start, start + length)


def loads(s):
    if not we_are_translated():
        import json
        data = json.loads(s)
        return _convert(data)
    decoder = JSONDecoder(s)
    try:
        w_res = decoder.decode_any(0)
        i = decoder.skip_whitespace(decoder.pos)
        if i < len(s):
            start = i
            end = len(s) - 1
            raise P4ParseError("Extra data: char %d - %d" % (start, end))
        return w_res
    finally:
        decoder.close()

def _convert(data):
    if data is None:
        return json_null
    if data is False:
        return json_false
    if data is True:
        return json_true
    if isinstance(data, int):
        return JsonInt(data)
    if isinstance(data, float):
        return JsonFloat(data)
    if isinstance(data, unicode):
        return JsonString(data.encode("utf-8"))
    if isinstance(data, list):
        return JsonArray([_convert(x) for x in data])
    if isinstance(data, dict):
        curr_map = ROOT_MAP
        values = []
        for (key, value) in data.iteritems():
            curr_map = curr_map.get_next(key.encode("utf-8"))
            values.append(_convert(value))
        return JsonObject.make(curr_map, values)


def dumps(json_obj):
    """
    Serialize a JsonBase object to a JSON string.

    Args:
        json_obj: A JsonBase instance to serialize

    Returns:
        A JSON string representation
    """
    fragments = []
    json_obj.dumps(fragments)
    return "".join(fragments)

