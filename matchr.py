#!/usr/bin/env python
# encoding: utf-8
# 
# regular expressions match combinator

import itertools
import functools
import sre_constants as sre
import sre_parse
import string


# public interface
def generate(pattern, max_repeat=sre.MAXREPEAT, flags=0):
    """A convenient interface to the match combinator.
    
    It parses a pattern (using `sre_parse.parse`), folds out all meta
    characters into a match tree (cf. `_generate`) and combines all regular
    subexpressions in order to obtain all possible matches (cf. `_combine`).

    It strips away all duplicates, as the pattern ``a?a?`` would yield ``''``,
    ``'a'``, ``'a'``, and ``'aa'`` otherwise.

    """
    # applying `set` right now would remove order
    matches = _combine(
        sre_parse.parse(pattern, flags=flags),
        max_repeat=max_repeat,
    )
    had = set()
    for match in matches:
        if match not in had:
            had.add(match)
            yield match

# itertools
try:
    from itertools import product
except ImportError:
    def product(*sets):
        """Cartesion product of input iterables by Steven Taschuk."""
        # http://code.activestate.com/recipes/159975/#c2
        wheels = map(iter, sets) # wheels like in an odometer
        digits = [it.next() for it in wheels]
        digits_n = len(digits)
        while True:
            yield digits[:]
            for i in xrange(digits_n-1, -1, -1):
                try:
                    digits[i] = wheels[i].next()
                    break
                except StopIteration:
                    wheels[i] = iter(sets[i])
                    digits[i] = wheels[i].next()
            else:
                break

def unpack(it):
    result = []
    for item in it:
        if isinstance(item, basestring):
            result.append(item)
        else:
            result.append(unpack(item))
    return result

# match generator
def _combine(sre_pattern, max_repeat):
    """Combine all matches from an SRE parsed pattern.

    Generate match sets first (cf. `_generate`) and apply the cartesian
    product to all sets.

    """
    return map(''.join,
        product(*unpack(_generate(sre_pattern, max_repeat=max_repeat))))
    # possible optimization: do not unpack but tee iterators
    # irrelevant at the moment since `product` is the biggest bottleneck

def _generate(sre_pattern, max_repeat):
    """Generate a sequence of match sets from an SRE parsed pattern.

    >>> g = functools.partial(_generate, max_repeat=3)
    >>> unpack(g([ # a*
    ...    ('max_repeat', (0, 65535, [
    ...      ('literal', 97),
           ])),
    ... ]))
    [['', 'a'], ['', 'a'], ['', 'a']]
    >>> unpack(g([ # (a|c)+
    ...    ('max_repeat', (1, 65535, [
    ...      ('subpattern', (1, [
    ...        ('in', [
    ...          ('literal', 97),
    ...          ('literal', 99),
    ...        ]),
    ...      ])),
    ...    ])),
    ... ]))
    [['a', 'c'], ['', 'a', 'c'], ['', 'a', 'c']]

    """
    g = functools.partial(_generate, max_repeat=max_repeat) # nested recursion
    c = functools.partial(_combine, max_repeat=max_repeat) # flat recursion

    for opcode, args in sre_pattern:

        if opcode == sre.SUBPATTERN:
            ref, pat = args
            yield c(pat)

        elif opcode == sre.BRANCH:
            none, branches = args
            yield itertools.chain(*map(c, branches))

        elif opcode == sre.LITERAL:
            yield chr(args)
        elif opcode == sre.NOT_LITERAL:
            yield sorted(ALL - set(chr(args)))

        elif opcode == sre.ANY:
            yield sorted(ALL)

        elif opcode == sre.RANGE:
            low, high = args
            yield itertools.imap(chr, xrange(low, high + 1))

        elif opcode == sre.IN:
            if args[0][0] == sre.NEGATE:
                args.pop(0)
                print args
                yield sorted(ALL - set(itertools.chain(*g(args))))
            else:
                yield itertools.chain(*g(args))

        elif opcode in (sre.MAX_REPEAT, sre.MIN_REPEAT):
            low, high, pat = args
            high = min(max_repeat, high)
            matches = c(pat)
            for i in xrange(low):
                yield matches
            for i in xrange(high - low):
                yield itertools.chain([EMPTY], matches)

        elif opcode == sre.CATEGORY:
            cat = args
            if cat in CATEGORIES:
                for char in CATEGORIES[cat]:
                    yield char
            else:
                raise NotImplementedError("category %s" % cat)

        else:
            if isinstance(args, basestring):
                args = "(%s,)" % args
            raise NotImplementedError("opcode %s %s" % (opcode, args))

# regular expressions
EMPTY = ''
ALL = set(itertools.imap(chr, itertools.ifilter(
    lambda x:x not in (10, 13, 0), xrange(256))))
CATEGORIES = {
    # these are all byte-safe and thus a sequence of strings
    sre.CATEGORY_DIGIT: string.digits,
    sre.CATEGORY_SPACE: string.whitespace,
    sre.CATEGORY_WORD: string.ascii_letters,

    sre.CATEGORY_NOT_DIGIT: sorted(ALL - set(string.digits)),
    sre.CATEGORY_NOT_SPACE: sorted(ALL - set(string.whitespace)),
    sre.CATEGORY_NOT_WORD: sorted(ALL - set(string.ascii_letters)),
}


if __name__ == '__main__':
    import optparse
    import sys
    optparse = optparse.OptionParser()
    optparse.add_option(
        "-p", "--parse-only",
        action='store_true',
        help="debug expression",
    )
    optparse.add_option(
        "-d", "--debug",
        action='store_true',
        help="show match structure",
    )
    optparse.add_option(
        "-c", "--count",
        action='store_true',
        help="print only a count of matches",
    )
    optparse.add_option(
        "-s", "--short",
        action='store_true',
        help="spare newlines on output",
    )
    optparse.add_option(
        "-r", "--repeat",
        type='int',
        help="override max_repeat", metavar="N",
        default=3,
    )
    optparse.add_option(
        "-a", "--ascii",
        action='store_true',
        help="use only printable ascii",
    )
    options, args = optparse.parse_args()
    args = ' '.join(args)

    if options.ascii:
        ALL = set(itertools.imap(chr, xrange(32, 127)))
    
    if options.count:
        for i, match in enumerate(generate(args, max_repeat=options.repeat)):
            pass
        print i + 1
    elif options.debug or options.parse_only:
        if options.parse_only:
            print sre_parse.parse(args)
        if options.debug:
            print unpack(_generate(sre_parse.parse(args), max_repeat=options.repeat))
    else:
        g = generate(args, max_repeat=options.repeat)
        if options.short:
            for match in g:
                print match,
        else:
            for match in g:
                print match
