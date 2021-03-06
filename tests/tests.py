import os
import re
import unittest
from array import array
from collections import defaultdict, deque, Set

import numpy

from tests.utils import TestCaseWithUtils, temp_attrs

try:
    from collections import Counter
except ImportError:
    from counter import Counter

try:
    from collections import OrderedDict
except ImportError:
    from ordereddict import OrderedDict

try:
    from collections import ChainMap
except ImportError:
    from chainmap import ChainMap

from cheap_repr import basic_repr, register_repr, cheap_repr, PY2, PY3, ReprSuppressedWarning, find_repr_function, \
    raise_exceptions_from_default_repr

os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.fake_django_settings'
import django

django.setup()
from django.contrib.contenttypes.models import ContentType


class FakeExpensiveReprClass(object):
    def __repr__(self):
        return 'bad'


register_repr(FakeExpensiveReprClass)(basic_repr)


class ErrorClass(object):
    def __init__(self, error=False):
        self.error = error

    def __repr__(self):
        if self.error:
            raise ValueError()
        return 'bob'


class ErrorClassChild(ErrorClass):
    pass


class OldStyleErrorClass:
    def __init__(self, error=False):
        self.error = error

    def __repr__(self):
        if self.error:
            raise ValueError()
        return 'bob'


class OldStyleErrorClassChild(OldStyleErrorClass):
    pass


class DirectRepr(object):
    def __init__(self, r):
        self.r = r

    def __repr__(self):
        return self.r


class RangeSet(Set):
    def __init__(self, length):
        self.length = length

    def __contains__(self, x):
        pass

    def __iter__(self):
        for x in range(self.length):
            yield x

    def __len__(self):
        return self.length


class TestCheapRepr(TestCaseWithUtils):
    maxDiff = None

    def assert_cheap_repr(self, x, expected_repr):
        self.assertEqual(
            re.sub(r'0x[0-9a-f]+', '0xXXX', cheap_repr(x)),
            expected_repr)

    def assert_usual_repr(self, x):
        self.assert_cheap_repr(x, repr(x))

    def assert_cheap_repr_evals(self, s):
        self.assert_cheap_repr(eval(s), s)

    def assert_cheap_repr_warns(self, x, message, expected_repr):
        self.assert_warns(ReprSuppressedWarning,
                          message,
                          lambda: self.assert_cheap_repr(x, expected_repr))

    def test_registered_default_repr(self):
        x = FakeExpensiveReprClass()
        self.assertEqual(repr(x), 'bad')
        self.assert_cheap_repr(x, r'<FakeExpensiveReprClass instance at 0xXXX>')

    def test_chain_map(self):
        self.assert_usual_repr(ChainMap({1: 2, 3: 4}, dict.fromkeys('abcd')))

        ex = ("ChainMap(["
              "OrderedDict([('1', 0), ('2', 0), ('3', 0), ('4', 0), ...]), "
              "OrderedDict([('1', 0), ('2', 0), ('3', 0), ('4', 0), ...]), "
              "OrderedDict([('1', 0), ('2', 0), ('3', 0), ('4', 0), ...]), "
              "OrderedDict([('1', 0), ('2', 0), ('3', 0), ('4', 0), ...]), "
              "OrderedDict([('1', 0), ('2', 0), ('3', 0), ('4', 0), ...]), "
              "OrderedDict([('1', 0), ('2', 0), ('3', 0), ('4', 0), ...]), "
              "...])")
        self.assert_cheap_repr(ChainMap([OrderedDict.fromkeys('1234567890', 0) for _ in range(10)]),
                               ex)

    def test_list(self):
        self.assert_usual_repr([])
        self.assert_usual_repr([1, 2, 3])
        self.assert_cheap_repr([1, 2, 3] * 10, '[1, 2, 3, 1, 2, 3, ...]')

    def test_tuple(self):
        self.assert_usual_repr(())
        self.assert_usual_repr((1,))
        self.assert_usual_repr((1, 2, 3))
        self.assert_cheap_repr((1, 2, 3) * 10, '(1, 2, 3, 1, 2, 3, ...)')

    def test_sets(self):
        self.assert_usual_repr(set())
        self.assert_usual_repr(frozenset())
        self.assert_usual_repr({1, 2, 3})
        self.assert_usual_repr(frozenset({1, 2, 3}))
        self.assert_cheap_repr(set(range(10)),
                               'set([0, 1, 2, 3, 4, 5, ...])' if PY2 else
                               '{0, 1, 2, 3, 4, 5, ...}')

    def test_dict(self):
        self.assert_usual_repr({})
        d1 = {1: 2, 2: 3, 3: 4}
        self.assert_usual_repr(d1)
        d2 = dict((x, x * 2) for x in range(10))
        self.assert_cheap_repr(d2, '{0: 0, 1: 2, 2: 4, 3: 6, ...}')

        if PY3:
            self.assert_usual_repr({}.keys())
            self.assert_usual_repr({}.values())
            self.assert_usual_repr({}.items())

            self.assert_usual_repr(d1.keys())
            self.assert_usual_repr(d1.values())
            self.assert_usual_repr(d1.items())

            self.assert_cheap_repr(d2.keys(),
                                   'dict_keys([0, 1, 2, 3, 4, 5, ...])')
            self.assert_cheap_repr(d2.values(),
                                   'dict_values([0, 2, 4, 6, 8, 10, ...])')
            self.assert_cheap_repr(d2.items(),
                                   'dict_items([(0, 0), (1, 2), (2, 4), (3, 6), ...])')

    def test_defaultdict(self):
        d = defaultdict(int)
        self.assert_usual_repr(d)
        d.update({1: 2, 2: 3, 3: 4})
        self.assert_usual_repr(d)
        d.update(dict((x, x * 2) for x in range(10)))
        self.assert_cheap_repr(d, "defaultdict(<class 'int'>, {0: 0, 1: 2, 2: 4, 3: 6, ...})")

    def test_deque(self):
        self.assert_usual_repr(deque())
        self.assert_usual_repr(deque([1, 2, 3]))
        self.assert_cheap_repr(deque(range(10)), 'deque([0, 1, 2, 3, 4, 5, ...])')

    def test_ordered_dict(self):
        self.assert_usual_repr(OrderedDict())
        self.assert_usual_repr(OrderedDict((x, x * 2) for x in range(3)))
        self.assert_cheap_repr(OrderedDict((x, x * 2) for x in range(10)),
                               'OrderedDict([(0, 0), (1, 2), (2, 4), (3, 6), ...])')

    def test_counter(self):
        self.assert_usual_repr(Counter())
        self.assert_cheap_repr_evals('Counter({0: 0, 2: 1, 4: 2})')
        self.assert_cheap_repr(Counter(dict((x * 2, x) for x in range(10))),
                               'Counter(10 keys)')

    def test_array(self):
        self.assert_usual_repr(array('l', []))
        self.assert_usual_repr(array('l', [1, 2, 3, 4, 5]))
        self.assert_cheap_repr(array('l', range(10)),
                               "array('l', [0, 1, 2, 3, 4, ...])")

    def test_numpy_array(self):
        self.assert_usual_repr(numpy.array([]))
        self.assert_usual_repr(numpy.array([1, 2, 3, 4, 5]))
        self.assert_cheap_repr(numpy.array(range(10)),
                               'array([0, 1, 2, 3, 4, 5, ...])')

    def test_bytes(self):
        self.assert_usual_repr(b'')
        self.assert_usual_repr(b'123')
        self.assert_cheap_repr(b'abc' * 50,
                               "b'abcabcabcabcabcabcabcabcabca...bcabcabcabcabcabcabcabcabcabc'")

    def test_str(self):
        self.assert_usual_repr('')
        self.assert_usual_repr(u'')
        self.assert_usual_repr(u'123')
        self.assert_usual_repr('123')
        self.assert_cheap_repr('abc' * 50,
                               "'abcabcabcabcabcabcabcabcabca...bcabcabcabcabcabcabcabcabcabc'")

    def test_django_queryset(self):
        self.assert_cheap_repr(ContentType.objects.all(),
                               '<QuerySet instance of ContentType at 0xXXX>')

    def test_inheritance(self):
        class A(object):
            def __init__(self):
                pass

        class B(A):
            pass

        class C(A):
            pass

        class D(C):
            pass

        class C2(C):
            pass

        class C3(C, B):
            pass

        class B2(B, C):
            pass

        class A2(A):
            pass

        @register_repr(A)
        def repr_A(_x, _helper):
            return 'A'

        @register_repr(C)
        def repr_C(_x, _helper):
            return 'C'

        @register_repr(B)
        def repr_B(_x, _helper):
            return 'B'

        @register_repr(D)
        def repr_D(_x, _helper):
            return 'D'

        self.assert_cheap_repr(A(), 'A')
        self.assert_cheap_repr(B(), 'B')
        self.assert_cheap_repr(C(), 'C')
        self.assert_cheap_repr(D(), 'D')
        self.assert_cheap_repr(C2(), 'C')
        self.assert_cheap_repr(C3(), 'C')
        self.assert_cheap_repr(B2(), 'B')
        self.assert_cheap_repr(A2(), 'A')

        self.assertEqual(find_repr_function(A), repr_A)
        self.assertEqual(find_repr_function(B), repr_B)
        self.assertEqual(find_repr_function(C), repr_C)
        self.assertEqual(find_repr_function(D), repr_D)
        self.assertEqual(find_repr_function(C2), repr_C)
        self.assertEqual(find_repr_function(C3), repr_C)
        self.assertEqual(find_repr_function(B2), repr_B)
        self.assertEqual(find_repr_function(A2), repr_A)

    def test_exceptions(self):
        with temp_attrs(cheap_repr, 'raise_exceptions', True):
            with self.assertRaises(ValueError):
                cheap_repr(ErrorClass(True))

        for C in [ErrorClass, OldStyleErrorClass]:
            name = C.__name__
            self.assert_usual_repr(C())
            self.assert_cheap_repr_warns(
                C(True),
                "Exception 'ValueError' in repr_object for object of type %s. "
                "The repr has been suppressed for this type." % name,
                '<%s instance at 0xXXX (exception in repr)>' % name,
            )
            self.assert_cheap_repr(C(), '<%s instance at 0xXXX (repr suppressed)>' % name)
        for C in [ErrorClassChild, OldStyleErrorClassChild]:
            name = C.__name__
            self.assert_cheap_repr(C(), '<%s instance at 0xXXX (repr suppressed)>' % name)

    def test_func_raise_exceptions(self):
        class T(object):
            pass

        @register_repr(T)
        def bad_repr(*_):
            raise TypeError()

        bad_repr.raise_exceptions = True

        with self.assertRaises(TypeError):
            cheap_repr(T())

        class X(object):
            def __repr__(self):
                raise IOError()

        class Y:  # old-style in python 2
            def __repr__(self):
                raise IOError()

        raise_exceptions_from_default_repr()

        for C in [X, Y]:
            with self.assertRaises(IOError):
                cheap_repr(C())

    def test_default_too_long(self):
        self.assert_usual_repr(DirectRepr('hello'))
        self.assert_cheap_repr_warns(
            DirectRepr('long' * 500),
            'DirectRepr.__repr__ is too long and has been suppressed. '
            'Register a repr for the class to avoid this warning '
            'and see an informative repr again, '
            'or increase cheap_repr.suppression_threshold',
            'longlonglonglonglonglonglong...glonglonglonglonglonglonglong')
        self.assert_cheap_repr(DirectRepr('hello'),
                               '<DirectRepr instance at 0xXXX (repr suppressed)>')

    def test_maxparts(self):
        self.assert_cheap_repr(list(range(8)),
                               '[0, 1, 2, 3, 4, 5, ...]')
        self.assert_cheap_repr(list(range(20)),
                               '[0, 1, 2, 3, 4, 5, ...]')
        with temp_attrs(find_repr_function(list), 'maxparts', 10):
            self.assert_cheap_repr(list(range(8)),
                                   '[0, 1, 2, 3, 4, 5, 6, 7]')
            self.assert_cheap_repr(list(range(20)),
                                   '[0, 1, 2, 3, 4, 5, 6, 7, 8, 9, ...]')

    def test_recursive(self):
        lst = [1, 2, 3]
        lst.append(lst)
        self.assert_cheap_repr(lst, '[1, 2, 3, [1, 2, 3, [1, 2, 3, [...]]]]')

        d = {1: 2, 3: 4}
        d[5] = d
        self.assert_cheap_repr(
            d, '{1: 2, 3: 4, 5: {1: 2, 3: 4, 5: {1: 2, 3: 4, 5: {...}}}}')

    def test_custom_set(self):
        self.assert_cheap_repr(RangeSet(0), 'RangeSet()')
        self.assert_cheap_repr(RangeSet(3), 'RangeSet({0, 1, 2})')
        self.assert_cheap_repr(RangeSet(10), 'RangeSet({0, 1, 2, 3, 4, 5, ...})')


if __name__ == '__main__':
    unittest.main()
