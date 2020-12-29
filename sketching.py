# Raw and simple.
# Pure funcs are actually just sensible (if slow) Python!
# Is it possible to interpret these with a vectorized semantics where they also
# take *intervals* for the dimensions, and return arrays?
inp = Buffer(UInt(16), 2)

@func
def blur_x(x, y):
    return (inp(x-1, y) + inp(x, y) + inp(x+1, y)) / 3

@func
def blur_y(x, y):
    return (blur_x(x-1, y) + blur_x(x, y) + blur_x(x+1, y)) / 3

# What about update stages?
# This seems potentially confusing.
# Do we close over the x,y of the parent?
# Do the vectorized semantics properly carry over?
@func # or @MultiStageFunc?
def multi_stage(x, y):
    @pure # or @Init or @func
    def init(x,y):
        return 0
    
    # This initialization can't be very general
    res = init(x,y)

    @update
    def upd():
        for i in seq(-1,1):
            for j in seq(-1,1):
                res += inp(x+i, y+j)
    
    return res # ugly/verbose, but clear/explicit?
    # What about applying the update(s)?
    #   like `return upd(res)`?

# What about a histogram & scan?
@func
def hist(i):
    @pure
    def init(i):
        return 0
    
    res = init(i)
    
    # Realizing: vectorized semantics will require a bounds inference pass/step.
    # The update clearly can't work with just a scalar `res`.
    # Alternate:
    res = init([min(0, i), max(255, i)])
    
    @update
    def upd():
        for y in seq(inp.height()):
            for x in seq(inp.width()):
                # Should this be (call) or [array index]?
                res(inp(x,y)) += 1

    # If the initialized interval is larger than i, then this should be sliced
    return res(i)

@func
def cdf(i):
    @pure 
    def init(i):
        return 0
    # This dummy init is getting tiresome!
    
    res = init(i)
    
    @update
    def upd():
        for i in seq(0, 255):
            res[i] = res[i-1]+hist(i)

@func
def normalized(x,y):
    return cdf(inp(x,y))

# Bounds inference with vectorized semantics would *mostly* just propagate
# bounds back to start, then pull forward. Main issue are update stages where
# the RDom also influences the bounds.
# Maybe this is manageable with some non-crazy rewrites in the decorator?
#   What would a bounds protocol compatible version of the histogram or cdf look
#   like?
#   It would have the computed interval set on the init, and the result sliced
#   out to return

# For the vectorized semantics to work without some vector calls in the return
# statement, this would probably have to be rewritten in the decorator to
# implicitly allocate the return buffer over x,y, then populate and return that:
@func
def test(x,y):
    return 0 # would not generate a vector, even if x,y were vectors

def test_transformed(x, y):
    res = alloc(x,y)
    res(x,y) = 0
    return res

# TODO: Are generators just functions which locally define and return Funcs?

# TODO: Try porting all of an app to see how it looks


###############
# Alternates
###############
# These are parameterized over inputs. Properly general, but verbose, and
# doesn't correspond to actual Halide
def blur_x(x : Var, y : Var, inp : Func):
    return (inp(x-1, y) + inp(x, y) + inp(x+1, y))/3

def blur_y(x : Var, y : Var, bx : Func):
    return (bx(x, y-1) + bx(x, y) + bx(x, y+1))/3

# TODO: What about return types? Consider setting / checking them?

#
# Stripped down update stage syntax
#
#   - If it's a multi-stage func, we don't need decorators inside. It should all
#     be defs, with the first a pure init, and the rest updates taking a result
#     buffer.
#
#   - Inner stage definitions DO NOT take Var arguments. They have to close over
#     the vars of the parent. If the  since those are the only dims which are
#     actually available. Paired with a simple syntactic rule that a multi-stage
#     func can ONLY contain a list of `def`s and no other statements, this
#     should syntactically (roughly) enforce a clear model of what is
#     semantically possible.
#
#   - Maybe the semantics aren't that bad? They hopefully just correspond to the
#     decorator implying that you add a final line to return the result of
#     applying each of the stages in order:
#     
#       return upd2(upd1(init())) # still implicitly closed over x,y
#     
#     For bounds inference of RDoms to work, this probably also requires that
#     init() first be extended to take explicit bounds, which are also computed
#     and inserted from all the update steps.
#
@func
def hist(i):
    def init():
        return 0

    def upd(res):
        for y in seq(inp.height()):
            for x in seq(inp.width()):
                # brackets for the result update, implying that it's a mutable
                # array at this point?
                res[inp(x,y)] += 1

@func
def blur(x, y):
    # Consider: default init to 0 is optional?
    
    # Consider: make update buffer argument optional, allow recursive use of
    #           func name instead?
    #
    # I actually think this is just less clear. The idea of having a mutable
    # result buffer for updates makes the model, and how these are different
    # from pure stages, seem significantly more obvious.
    def upd():
        for i in seq(-1,1):
            for j in seq(-1,1):
                blur[x,y] += inp(x+i, y+j)

@func
def iir_blur(x, y):
    def init():
        return undef(float)
    
    def init_top(buf):
        buf[x, 0] = inp(x, 0)
    
    def down_columns(res):
        for ry in seq(1, height):
            res[x, ry] = (1 - alpha) * res(x, ry - 1) + alpha * input(x, ry)
    
    def up_columns(res):
        for ry in seq(1, height):
            flip_ry = height - y - 1 # this just becomes an Expr
            res[x, flip_ry] = (1 - alpha) * res[x, flip_ry + 1] + alpha * res[x, flip_ry]
        