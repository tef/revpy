import sys
import types

from opcode import *

def rev(x=None):
    if x is None:
        x = get_trackback()
    if type(x) is types.InstanceType:
        x = x.__class__
    if hasattr(x, 'im_func'):
        x = x.im_func
    if hasattr(x, 'func_code'):
        x = x.func_code
    if hasattr(x, '__dict__'):
        return reverse_class(x)
    elif hasattr(x, 'co_code'):
        return reverse(x)
    elif isinstance(x, str):
        return reverse_string(x)
    else:
        raise TypeError, \
              "don't know how to reverse%s objects" % \
              type(x).__name__

def get_trackback(tb=None):
    if tb is None:
        try:
            tb = sys.last_traceback
        except AttributeError:
            raise RuntimeError, "no last traceback to disassemble"
        while tb.tb_next: tb = tb.tb_next
    reverse(tb.tb_frame.f_code, tb.tb_lasti)

def reverse_class(x):
        items = x.__dict__.items()
        items.sort()
        for name, x1 in items:
            if type(x1) in (types.MethodType,
                            types.FunctionType,
                            types.CodeType,
                            types.ClassType):
                print "Disassembly of %s:" % name
                try:
                    reverse(x1)
                except TypeError, msg:
                    print "Sorry:", msg
                print

def reverse(co, lasti=-1):
    r = Reverser(co, lasti)
    return r.rev()



class Reverser(object):

    def __init__(self, co, lasti=-1):
        self.code = co.co_code
        self.labels = findlabels(self.code)
        self.linestarts = dict(findlinestarts(co))
        self.n = len(self.code)
        self.lasti = lasti
        self.co = co

    def rev(self):
        i = 0
        extended_arg = 0
        free = None
        while i < self.n:
            c = self.code[i]
            op = ord(c)
            if i in self.linestarts:
                if i > 0:
                    print
                print "%3d" % self.linestarts[i],
            else:
                print '   ',

            if i == self.lasti: print '-->',
            else: print '   ',
            if i in self.labels: print '>>',
            else: print '  ',
            print repr(i).rjust(4),
            print opname[op].ljust(20),
            i = i+1
            if op >= HAVE_ARGUMENT:
                oparg = ord(self.code[i]) + ord(self.code[i+1])*256 + extended_arg
                extended_arg = 0
                i = i+2
                if op == EXTENDED_ARG:
                    extended_arg = oparg*65536L
                print repr(oparg).rjust(5),
                if op in hasconst:
                    print '(' + repr(self.co.co_consts[oparg]) + ')',
                elif op in hasname:
                    print '(' + self.co.co_names[oparg] + ')',
                elif op in hasjrel:
                    print '(to ' + repr(i + oparg) + ')',
                elif op in haslocal:
                    print '(' + self.co.co_varnames[oparg] + ')',
                elif op in hascompare:
                    print '(' + cmp_op[oparg] + ')',
                elif op in hasfree:
                    if free is None:
                        free = co.co_cellvars + co.co_freevars
                    print '(' + free[oparg] + ')',
            print

def reversee_string(code, lasti=-1, varnames=None, names=None,
                       constants=None):
    labels = findlabels(code)
    n = len(code)
    i = 0
    while i < n:
        c = code[i]
        op = ord(c)
        if i == lasti: print '-->',
        else: print '   ',
        if i in labels: print '>>',
        else: print '  ',
        print repr(i).rjust(4),
        print opname[op].ljust(15),
        i = i+1
        if op >= HAVE_ARGUMENT:
            oparg = ord(code[i]) + ord(code[i+1])*256
            i = i+2
            print repr(oparg).rjust(5),
            if op in hasconst:
                if constants:
                    print '(' + repr(constants[oparg]) + ')',
                else:
                    print '(%d)'%oparg,
            elif op in hasname:
                if names is not None:
                    print '(' + names[oparg] + ')',
                else:
                    print '(%d)'%oparg,
            elif op in hasjrel:
                print '(to ' + repr(i + oparg) + ')',
            elif op in haslocal:
                if varnames:
                    print '(' + varnames[oparg] + ')',
                else:
                    print '(%d)' % oparg,
            elif op in hascompare:
                print '(' + cmp_op[oparg] + ')',
        print


def findlabels(code):
    """Detect all offsets in a byte code which are jump targets.

    Return the list of offsets.

    """
    labels = []
    n = len(code)
    i = 0
    while i < n:
        c = code[i]
        op = ord(c)
        i = i+1
        if op >= HAVE_ARGUMENT:
            oparg = ord(code[i]) + ord(code[i+1])*256
            i = i+2
            label = -1
            if op in hasjrel:
                label = i+oparg
            elif op in hasjabs:
                label = oparg
            if label >= 0:
                if label not in labels:
                    labels.append(label)
    return labels

def findlinestarts(code):
    """Find the offsets in a byte code which are start of lines in the source.

    Generate pairs (offset, lineno) as described in Python/compile.c.

    """
    byte_increments = [ord(c) for c in code.co_lnotab[0::2]]
    line_increments = [ord(c) for c in code.co_lnotab[1::2]]

    lastlineno = None
    lineno = code.co_firstlineno
    addr = 0
    for byte_incr, line_incr in zip(byte_increments, line_increments):
        if byte_incr:
            if lineno != lastlineno:
                yield (addr, lineno)
                lastlineno = lineno
            addr += byte_incr
        lineno += line_incr
    if lineno != lastlineno:
        yield (addr, lineno)

def _test():
    """Simple test program to disassemble a file."""
    if sys.argv[1:]:
        if sys.argv[2:]:
            sys.stderr.write("usage: python dis.py [-|file]\n")
            sys.exit(2)
        fn = sys.argv[1]
        if not fn or fn == "-":
            fn = None
    else:
        fn = None
    if fn is None:
        f = sys.stdin
    else:
        f = open(fn)
    source = f.read()
    if fn is not None:
        f.close()
    else:
        fn = "<stdin>"
    code = compile(source, fn, "exec")
    print rev(code)

if __name__ == "__main__":
    _test()
