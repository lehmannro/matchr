#!/usr/bin/env python
# encoding: utf-8
# 
# regular expressions match combinator

import itertools
import functools
import sre_constants as sre
import sre_parse

EMPTY = ''

# public interface
def generate(pattern, max_repeat, flags=0):
    had = [] # avoid duplicates
    # otherwise eg. a?a? would yield '', 'a', 'a', 'aa'
    g = gen(sre_parse.parse(pattern, flags=flags), max_repeat=max_repeat)
    for mat in comb(g):
        mat = ''.join(mat)
        if mat not in had:
            had.append(mat)
            yield mat

# itertools
def unpack(g):
    r = []
    for mat in g:
        if isinstance(mat, basestring):
            r.append(mat)
        else:
            r.append(unpack(mat))
    return r

def joinprod(a ,b):
    """Cartesian product"""
    for item_a in a:
        for item_b in b:
            yield item_a + item_b

# match structures
def comb(g):
    """Fold out a nested match structure."""
    r = [[]]
    for mat in g:
        if isinstance(mat, basestring):
            for p in r:
                p.append(mat)
        else: # mat = [A, B] means A OR B where A, B are AND structures
            mat = map(comb, mat)
            r = list(itertools.chain(*map(lambda b:list(joinprod(r, b)), mat)))
    return r

def gen(sre_pattern, max_repeat=sre.MAXREPEAT):
    """Generate a nested match structure from an SRE parsed pattern.

    Odd levels of nesting indicate concatenation,
    even levels of nesting indicate alternation.

    ====================== ==================
        Match structure    Regular Expression
    ====================== ==================
    ``[A, [[B], [C]]]``    ``A(B|C)``
    ``[A, [[B, C], [D]]]`` ``A(BC|D)``
    ``[A, [[], [B]]]``     ``AB?``
    ====================== ==================

    """
    _gen = functools.partial(gen, max_repeat=max_repeat)
    for opcode, args in sre_pattern:
        if opcode == sre.LITERAL:
            yield chr(args)
        elif opcode == sre.RANGE:
            low, high = args
            for char in xrange(low, high + 1):
                yield chr(char)
        elif opcode == sre.IN:
            yield _gen(args)
        elif opcode == sre.MAX_REPEAT: # A{l,h}
            low, high, pat = args
            high = min(max_repeat, high)
            pat = unpack(_gen(pat))
            for i in xrange(low): # A{l}
                yield (pat,)
            for i in xrange(high - low): # (A?){h-l}
                yield ([EMPTY], pat)
        elif opcode == sre.SUBPATTERN:
            ref, pat = args
            pat = _gen(pat)
            for p in pat:
                yield p
        elif opcode == sre.BRANCH:
            none, branches = args
            yield map(_gen, branches)
        elif opcode == sre.ANY:
            yield map(chr, itertools.ifilter(lambda x:x not in (13, 10),
                xrange(256)))
        elif opcode == sre.CATEGORY:
            cat = args
            if cat == sre.CATEGORY_DIGIT:
                for c in xrange(10):
                    yield str(c)
            else:
                raise NotImplementedError("%s in %s" %
                    (cat, ", ".join(map(repr, sre_pattern))))
        else:
            raise NotImplementedError("%s in %s" %
                (opcode, ", ".join(map(repr, sre_pattern))))

if __name__ == '__main__':
    import optparse
    import sys
    optparse = optparse.OptionParser()
    optparse.add_option(
        "-d", "--debug",
        action='store_true',
        help="debug expression",
    )
    optparse.add_option(
        "-q", "--quiet",
        action='store_true',
        help="do not combine matches",
    )
    optparse.add_option(
        "-c", "--count",
        action='store_true',
        help="only output the number of combined matches",
    )
    optparse.add_option(
        "-s", "--short",
        action='store_true',
        help="do not allocate an extra line for each match",
    )
    optparse.add_option(
        "-n", "--nest",
        action='store_true',
        help="show nested match",
    )
    optparse.add_option(
        "-r", "--repeat",
        type='int',
        help="override max_repeat", metavar="N",
        default=3,
    )
    options, args = optparse.parse_args()
    args = ' '.join(args)

    if options.count:
        for i, mat in enumerate(generate(args, max_repeat=options.repeat)):
            pass
        print i+1
        sys.exit()
    if options.debug:
        print sre_parse.parse(args)
    if options.nest:
        print unpack(gen(sre_parse.parse(args), max_repeat=options.repeat))
    if not options.quiet:
        g = generate(args, max_repeat=options.repeat)
        if options.short:
            for mat in g:
                print mat,
        else:
            for mat in g:
                print mat
