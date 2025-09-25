import py

from rpython.rlib.unroll import unrolling_iterable
from rpython.rlib        import jit, debug, objectmodel

def _not_null(s_arg, bookkeeper):
    return not s_arg.can_be_None

def inline_small_list(sizemax=5, sizemin=0, immutable=False, nonull=False,
                      attrname="list", factoryname="make", listgettername="_get_full_list",
                      listsizename="_get_size_list", gettername="_get_list",
                      settername="_set_list"):
    """
    This function is helpful if you have a class with a field storing a
    list and the list is often very small. Calling this function will inline
    the list into instances for the small sizes. This works by adding the
    following methods (names customizable) to the class:

    _get_list(self, i): return ith element of the list

    _set_list(self, i, val): set ith element of the list

    _get_full_list(self): returns a copy of the full list

    _get_size_list(self): returns the length of the list

    @staticmethod
    make(listcontent, *args): makes a new instance with the list's content set to listcontent
    """
    assert sizemin == 0
    def wrapper(cls):

        _immutable_ = getattr(cls, "_immutable_", False)
        empty_list = []

        def make_class0():
            # construct the base class, the other specific-size-classes inherit from it
            attrs = ["_%s_%s" % (attrname, i) for i in range(sizemax - 1)]
            unrolling_enumerate_attrs = unrolling_iterable(enumerate(attrs))

            def _get_size_list(self):
                return self._size_list

            def _get_list(self, i):
                for j, attr in unrolling_enumerate_attrs:
                    if j == i:
                        if not isinstance(self, classes[j + 1]):
                            break
                        result = getattr(self, attr)
                        if nonull:
                            debug.check_annotation(result, _not_null)
                        return result
                raise IndexError
            def _get_full_list(self):
                return empty_list
            def _set_list(self, i, val):
                if nonull:
                    assert val is not None
                for j, attr in unrolling_enumerate_attrs:
                    if j == i:
                        if not isinstance(self, classes[j + 1]):
                            break
                        setattr(self, attr, val)
                        return
                raise IndexError
            def _init(self, elems, *args):
                assert len(elems) == 0
                cls.__init__(self, *args)

            # Methods for the new class being built
            methods = {
                gettername     : _get_list,
                listsizename   : _get_size_list,
                listgettername : _get_full_list,
                settername     : _set_list,
                "__init__"     : _init,
                "_size_list"   : 0,
            }

            newcls = type(cls)("%sSize0" % (cls.__name__, ), (cls, ), methods)
            if "_attrs_" in cls.__dict__:
                setattr(newcls, "_attrs_", [])

            return newcls

        def make_class(size, base):
            attrs = ["_%s_%s" % (attrname, i) for i in range(size)]
            unrolling_enumerate_attrs = unrolling_iterable(enumerate(attrs))

            def _get_full_list(self):
                if size == 0:
                    return empty_list
                res = [None] * size
                for i, attr in unrolling_enumerate_attrs:
                    elem = getattr(self, attr)
                    if nonull:
                        debug.check_annotation(elem, _not_null)
                    res[i] = getattr(self, attr)
                return res
            def _init(self, elems, *args):
                assert len(elems) == size
                for i, attr in unrolling_enumerate_attrs:
                    val = elems[i]
                    if nonull:
                        assert val is not None
                    setattr(self, attr, elems[i])
                cls.__init__(self, *args)

            # Methods for the new class being built
            methods = {
                listgettername : _get_full_list,
                "__init__"     : _init,
                "_size_list"   : size,
            }

            newcls = type(cls)("%sSize%s" % (cls.__name__, size), (base, ), methods)

            if immutable:
                setattr(newcls, "_immutable_fields_", attrs)

            if "_attrs_" in cls.__dict__:
                setattr(newcls, "_attrs_", attrs)

            return newcls

        classes = []
        for i in range(sizemin, sizemax):
            if i == 0:
                prev = make_class0()
            else:
                prev = make_class(i, prev)
            classes.append(prev)

        # Build the arbitrary sized variant
        def _get_arbitrary(self, i):
            return getattr(self, attrname)[i]
        def _get_size_list_arbitrary(self):
            return len(getattr(self, attrname))
        def _get_list_arbitrary(self):
            return getattr(self, attrname)
        def _set_arbitrary(self, i, val):
            if nonull:
                assert val is not None
            getattr(self, attrname)[i] = val
        def _init(self, elems, *args):
            debug.make_sure_not_resized(elems)
            setattr(self, attrname, elems)
            cls.__init__(self, *args)

        methods = {
            gettername     : _get_arbitrary,
            listsizename   : _get_size_list_arbitrary,
            listgettername : _get_list_arbitrary,
            settername     : _set_arbitrary,
            "__init__"     : _init,
        }

        cls_arbitrary = type(cls)("%sArbitrary" % cls.__name__, (cls, ), methods)

        if _immutable_:
            setattr(cls_arbitrary, "_immutable_", True)
        if immutable:
            setattr(cls_arbitrary, "_immutable_fields_", ["%s[*]" % (attrname,)])

        if "_attrs_" in cls.__dict__:
            setattr(cls_arbitrary, "_attrs_", attrname)

        def make(elems, *args):
            if classes:
                if (elems is None or len(elems) == 0):
                    return make0(*args)
            else:
                if elems is None:
                    elems = []
            if sizemin <= len(elems) < sizemax:
                cls = classes[len(elems) - sizemin]
            else:
                cls = cls_arbitrary
            return cls(elems, *args)

        # XXX those could be done more nicely
        def make0(*args):
            if not classes: # no type specialization
                return make([], *args)
            result = objectmodel.instantiate(classes[0])
            cls.__init__(result, *args)
            return result
        def make1(elem, *args):
            if not classes: # no type specialization
                return make([elem], *args)
            result = objectmodel.instantiate(classes[1])
            result._set_list(0, elem)
            cls.__init__(result, *args)
            return result
        def make2(elem1, elem2, *args):
            if not classes: # no type specialization
                return make([elem1, elem2], *args)
            result = objectmodel.instantiate(classes[2])
            result._set_list(0, elem1)
            result._set_list(1, elem2)
            cls.__init__(result, *args)
            return result

        def make_n(size, *args):
            if sizemin <= size < sizemax:
                subcls = classes[size - sizemin]
            else:
                subcls = cls_arbitrary
            result = objectmodel.instantiate(subcls)
            if subcls is cls_arbitrary:
                assert isinstance(result, subcls)
                setattr(result, attrname, [None] * size)
            cls.__init__(result, *args)
            return result

        setattr(cls, factoryname, staticmethod(make))
        setattr(cls, factoryname + "0", staticmethod(make0))
        setattr(cls, factoryname + "1", staticmethod(make1))
        setattr(cls, factoryname + "2", staticmethod(make2))
        setattr(cls, factoryname + "_n", staticmethod(make_n))
        return cls
    return wrapper

