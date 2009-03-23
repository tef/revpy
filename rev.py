import sys
import types
import random


""" python decompiler
todo: print_item_to
list_append
load_locals
import* import name import from
build_class
withcleanup

except/finally/raise_vargargs
/make_closure
build_slice
from opcode import *
"""
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

def build(name, args):
    t = [name]
    if args:
        t.extend(args)
    return tuple(t)

def reverse(co, lasti=-1):
    r = Reverser(co, lasti)
    _,o = r.reverse()
    return o
    
def add_expr(new_expr,python, out):
    if new_expr and len(out) == 1 and isinstance(out[0],tuple) and  out[0][0].startswith("print"):
        if len(python) > 0 and isinstance(python[-1],tuple) and python[-1][0].startswith("print"):
            one = python.pop()
            args = list(one[1:])
            args.extend(out[0][1:])
            out = [build("print", args)]
    python.extend(out)

class Reverser(object):
    def __init__(self, co, lasti=-1):
        self.co = co
        self.code = co.co_code
        self.linestarts = dict(findlinestarts(co))
        self.n = len(self.code)
        self.free = None
        self.lasti = lasti

    def reverse(self, i=0, terminator = "STOP_CODE"):
        python = []
        stack = []
        new_expr=True
        while i < self.n:
            if (i in self.linestarts):
                new_expr = False
            i,out = self.reverse_one(stack, i, terminator)
            if isinstance(out,str) and out.startswith(terminator):
                break
            add_expr(new_expr,python,out)
            if out:
                new_expr = True
        #print "end", stack 
        for i in reversed(stack):
            add_expr(True,python,i)
        return i,python
        
    def reverse_one(self,stack, i, terminator):
        python = []
        if i == self.lasti: 
            python.append("# Current Line")
        i,name, arg, oparg = self.instr(i)
        #print "rev1:",name, terminator
        if name.startswith("INPLACE_"):
            one = stack.pop()
            two = stack.pop()
            name = name.lower()
            python.append(build(name,[two,one]))
        elif name.startswith("UNARY_") or name == "GET_ITER":
            one = stack.pop()
            name = name[(name.find("_")+1):].lower()
            stack.append(build(name,[one]))
        elif name == "COMPARE_OP":
            one = stack.pop()
            two = stack.pop()
            stack.append(build(arg,[two,one]))
        elif name.startswith("BINARY_"):
            one = stack.pop()
            two = stack.pop()
            name = name[(name.find("_")+1):].lower()
            stack.append(build(name,[two,one]))
        elif name.find("ATTR") > 0:
            one = stack.pop()
            stack.append(build("attr",[one,arg]))
        elif name.find("SUBSCR") > 0:
            one = stack.pop()
            two = stack.pop()
            stack.append(build("subscr",[two,one]))
        elif name.find("SLICE") > 0:
            n = int(name[-1])
            one = stack.pop()
            if n == 0:
                stack.append(build("sliceall",[one]))
            else:
                two = stack.pop()
                if n == 1:
                    stack.append(build("sliceleft",[two,one]))
                elif n == 2:
                    stack.append(build("sliceright",[two,one]))
                else:
                    three = stack.pop()
                stack.append(build("slice",[three,two,one]))
        elif name.startswith("LOAD_"):
            stack.append(arg)
                
        if name.startswith(terminator):
            return i,name
        elif name == "RETURN_VALUE" or name == "YIELD_VALUE":
            one = stack.pop()
            python.append(build(name[:name.find("_")].lower(),[one]))
        elif name == "NOP":
            pass
        elif name == "SETUP_LOOP":
            end = i + int(oparg) 
            start = i
            body = []
            cond = True
            wloop = True
            new_expr = True
            #print "loop", i, end
            while  i < end:
                if (i in self.linestarts):
                    new_expr = False
                n,name, arg, oparg = self.instr(i)
                if name.startswith("JUMP_") and name.find("IF") > 0 and oparg + n == (end-2):
                            #print "exit found", body
                            if len(body) > 1:
                                raise Exception, "Fuck"
                            cond = body[0]
                            body = []
                            #print "ijmp",n
                            i = n+1
                            if name.find("TRUE") > 0:
                                cond = ('not', cond)
                elif name == "FOR_ITER" and oparg + n == (end-1):
                            if len(body) > 1:
                                raise Exception, "Fuck"
                            wloop=False
                            #print "exit found", body
                            v = "__s"+str(random.randint(0,1024))
                            cond = build("set",[v,body[0]])
                            body = [v]
                            start = i
                            i = n
                else:
                        i,out = self.reverse_one(body,i,terminator="STOP_CODE")
                        add_expr(new_expr,body,out)
                        if out:
                            new_expr = True
                if i == start:
                    i = end + 2
                    break;
            python.append(build("while" if wloop else "for",[cond, body]))
                
        elif name == "JUMP_FORWARD":
            i = i+ int(oparg)
        elif name == "JUMP_ABSOLUTE":
            #print "hump",oparg
            i = int(oparg)
        elif name.startswith("JUMP"): # must be an if statement
            start = i
            i+=1
            jmp = i + int(oparg) 
            if jmp <  i:
                raise Exception, "fuck"
            if_branch = []
            new_expr = True
            cond = stack.pop()
            oldstack = stack[:]
            while start < i < jmp :
                if (i in self.linestarts):
                    new_expr = False
                i,out = self.reverse_one(stack, i, terminator="STOP_CODE")
                add_expr(new_expr,if_branch,out)
                if out:
                    new_expr = True
            else_branch = []
            new_expr = True
            stack = oldstack
            while jmp != i:
                if (jmp in self.linestarts):
                    new_expr = False
                jmp,out = self.reverse_one(stack, jmp, terminator="STOP_CODE")
                add_expr(new_expr,else_branch,out)
                if out:
                    new_expr = True
            if jmp != i or len(stack) > 0:
                raise Exception, "fuck"
            if  name[8:] == "FALSE":
                if_branch, else_branch = else_branch, if_branch
            if len(else_branch) == 1 and isinstance(else_branch[0], tuple) and else_branch[0][0] == "if":
                args = [cond, if_branch].append(else_branch[0][1:])
                python.append(build("if",args))  
            else:
                python.append(build("if",[cond,if_branch,else_branch]))  
        elif name.startswith("BUILD_"):
            n = int(oparg)
            args = []
            while n > 0:
                args.append(stack.pop())
                n-=1
            args.reverse()
            v = "__s"+str(random.randint(0,1024))
            python.append(build("set",[v,build(name.lower(),args)]))
            stack.append(v)

        elif name == "POP_TOP":
            one = stack.pop()
            #python.append(one)
        elif name == "DUP_TOP":
            stack.append(stack[-1])
        elif name == "ROT_TWO":
            one = stack.pop()
            two = stack.pop()
            stack.append(one)
            stack.append(two)
        elif name == "ROT_THREE":
            one = stack.pop()
            two = stack.pop()
            three = stack.pop()
            stack.append(one)
            stack.append(three)
            stack.append(two)
        elif name == "ROT_FOUR":
            one = stack.pop()
            two = stack.pop()
            three = stack.pop()
            four = stack.pop()
            stack.append(one)
            stack.append(four)
            stack.append(three)
        elif name == "EXEC_STMT":
            one = stack.pop() if len(stack) > 2 else None
            two = stack.pop() if len(stack) > 1 else None
            three = stack.pop()
            python.append(build("exec",(three,two,one)))
        elif name.startswith("STORE"):
            func = name[(name.find("_")+1):].lower()
            one = arg if func in ['global','fast','name']  else stack.pop()
            two = stack.pop()
            python.append(build("set",[one,two]))
        elif name.endswith("LOOP"):
            func = name[:name.find("_")].lower()
            python.append(build(func,[]))
        elif name == "RAISE_VARARGS":
            args = []
            low = oparg
            while low > 0:
                a=stack.pop()
                args.append(a)
                low-=1
            python.append(build("raise",args[0:2]))
        elif name.startswith("CALL_FUNCTION"):
            kkargs = stack.pop() if name.find("_KW") > 0 else {}
            ppargs = stack.pop() if name.find("_VAR") > 0 else []
            low, high = oparg & 255, oparg >> 8
            pargs = []
            while low > 0:
                a=stack.pop()
                pargs.append(a)
                low-=1
            pargs.reverse()
            kargs = {}
            while high > 0:
                a=stack.pop()
                b=stack.pop()
                kargs[a] = b
                high-=1
            func = stack.pop()
            v = "__s"+str(random.randint(0,1024))
            stack.append(v)
            python.append(build('set',[v,('call',func,pargs,kargs,ppargs,kkargs)]))
        elif name == "UNPACK_SEQUENCE":
            one = stack.pop()
            args = []
            n = oparg
            while n > 0:
                v = "__s"+str(random.randint(0,1024))
                stack.append(v)
                args.append(v)
                n-=1
            args.reverse()
            python.append(build("set",[args,one]))
        elif name == "DUP_TOPX":
            newstack = []
            n = oparg
            while n > 0:
                a = stack.pop()
                newstack.extend([a,a])
            stack.extend(newstack)
        elif name.startswith("DELETE"):
            func = name[(name.find("_")+1):].lower()
            one = arg if func in ['global','fast','name']  else stack.pop()
            python.append(build("del",[one]))
        elif name.startswith("PRINT"):
            if name.endswith("TO"):
                raise Exception,"fuck"
            one = [[name[name.find("_")+1:].lower(),stack.pop()]] if name != "PRINT_NEWLINE" else [["newline"]]
            python.append(build("print",one))
                
        return i,python

    def instr(self, i):
        print i
        extended_arg = 0
        c = self.code[i]
        op = ord(c)
        arg = None
        oparg = None
        name = opname[op]
        i+=1
        if op >= HAVE_ARGUMENT:
            oparg = ord(self.code[i]) + ord(self.code[i+1])*256 + extended_arg
            extended_arg = 0
            i = i+2
            arg = None
            if op == EXTENDED_ARG:
                extended_arg = oparg*65536L
            if op in hasconst:
                arg =  self.co.co_consts[oparg]
            elif op in hasname:
                arg = self.co.co_names[oparg]
            elif op in hasjrel:
                arg = i + oparg
            elif op in haslocal:
                arg = self.co.co_varnames[oparg]
            elif op in hascompare:
                arg =  cmp_op[oparg]
            elif op in hasfree:
                if self.free is None:
                    self.free = self.co.co_cellvars + self.co.co_freevars
                arg =  self.free[oparg]
            if arg and isinstance(arg,tuple):
                arg = tuple(['tuple'].append(arg))
        return i,name, arg, oparg


operators = {
    'add':'+',
    'attr':'.',
}
def ast_to_code(tree):
    if tree[0] in operators:
        pass
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
