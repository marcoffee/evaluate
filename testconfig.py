import os
import glob
import operator as op
import itertools as it
import collections as cl


REMOVE = False
ENABLE = True

class Exp (object):
    def __init__ (self, a, logic, b):
        self.a = a
        self.logic = logic
        self.b = b

    def __iter__ (self):
        yield self.a
        yield self.logic
        yield self.b

class ExpError (Exception):
    pass

def sanitize_value (value, prec):
    if not isinstance(value, str) and isinstance(value, cl.Iterable):
        return "[{}]".format(",".join(sanitize_value(v, prec) for v in sorted(value)))

    if value is REMOVE or value is ENABLE:
        return value

    return format(value, ".{}f".format(prec) if isinstance(value, float) else "")

def sanitize_exp (flags, prec = 3):
    for k, v in sorted(flags.items()):
        k = k.strip("-")

        if v is REMOVE:
            continue

        if v is ENABLE:
            yield k,
        else:
            yield k, sanitize_value(v, prec)

def parse_flags (expe):
    for val in expe:
        if len(val) >= 2:
            yield val[0], val[1]
        else:
            yield val[0], ENABLE

def get_name (file):
    return os.path.splitext(os.path.basename(file))[0]

def get_fname (expe):
    if expe:
        return ";".join(map("=".join, expe))

    return "-"

def parse_ops (ops, flags):
    opa, logic, opb = ops

    if isinstance(opa, Exp):
        if not isinstance(opb, Exp):
            raise ExpError(
                "If operator a is expression, "
                "b should also be expression."
            )

        opa = parse_ops(opa, flags)
        opb = parse_ops(opb, flags)

        return logic(opa, opb)
    return logic(flags.get(opa, None), opb)

def ignore_exp (flags, ignore):
    for ign in ignore:
        if parse_ops(ign, flags):
            return True

    return False

def iter_tests ():
    for benchmarks, params, values in tests:
        experiments = []

        for value in it.product(*values):
            flags = { **default, **dict(zip(params, value)) }

            if ignore_exp(flags, ignore):
                continue

            experiments.append(flags)

        experiments = tuple(experiments)

        print(experiments)

        for benchmark in benchmarks:
            yield benchmark, experiments

def disable_quiet ():
    fixed["-quiet"] = REMOVE

def create_file (fname):
    try:
        with open(fname, "x"):
            pass

    except FileExistsError:
        pass


# benchmarks-1
# benchmarks-2
# ...
benchmarks = [] # benchmarks-1 + benchmarks-2 + ...

default_test = ( benchmarks, [], [] )

# tests to evaluate
# all parameters should not be positional
tests = [
# (
    # benchmarks-1,
    # [       "-test-1-param-1",       "-test-2-param-2", ... ],
    # [ [ t1p1v1, t1p1v2, ... ], [ t1p2v1, t1p2v2, ... ], ... ],
# ), (
    # benchmarks-2
    # [       "-test-2-param-1",       "-test-2-param-2", ... ],
    # [ [ t2p1v1, t2p1v2, ... ], [ t2p2v1, t2p2v2, ... ], ... ],
# )
]

# combinations to ignore
ignore = [
    # Exp(Exp( "-param-ignore-1-1", compare, value-ignore-1-1 ), operator,
    #     Exp( "-param-ignore-2-1", compare, value-ignore-2-1 )),
    #
    # Exp(Exp( "-param-ignore-1-2", compare, value-ignore-1-2 ), operator,
    #     Exp( "-param-ignore-2-2", compare, value-ignore-2-2 )),
]

# default values when param not found in a test
# should exists for every param (and only these) defined in tests
default = {
    # "-param-1-default"  : value-default-1,
    # "-param-2-default"  : value-default-2,
}

# fixed parameters and their values
# these parameters will never change
fixed = {
    # "-param-1-fixed" : value-fixed-1
    # "-param-2-fixed" : value-fixed-2
}

seed_start = 0 # starting seed
seed_stop = 30 # stopping seed

rst_path = "results" # results directory
plt_path = "plots"   # plots directory
tre_path = "treated" # treated benchmarks data directory

deq_path = "work"     # worker / deque directory
deq_name = "deque"    # deque name

tst_file = "./tested.txt"   # tested file
siz_file = "./exp-size.txt" # experiment size file

tests = tests or [ default_test ]

rst_path = os.path.realpath(rst_path)
plt_path = os.path.realpath(plt_path)
deq_path = os.path.realpath(deq_path)
tre_path = os.path.realpath(tre_path)
tst_path = os.path.realpath(os.path.dirname(tst_file))
siz_path = os.path.realpath(os.path.dirname(siz_file))

os.makedirs(rst_path, exist_ok = True)
os.makedirs(plt_path, exist_ok = True)
os.makedirs(deq_path, exist_ok = True)
os.makedirs(tre_path, exist_ok = True)
os.makedirs(tst_path, exist_ok = True)
os.makedirs(siz_path, exist_ok = True)

tst_file = os.path.join(tst_path, os.path.basename(tst_file))
siz_file = os.path.join(siz_path, os.path.basename(siz_file))

create_file(tst_file)
create_file(siz_file)
