# Raw and simple.
# Pure funcs are actually just sensible (if slow) Python!
# Is it possible to interpret these with a vectorized semantics where they also take *intervals* for the dimensions, and return arrays?
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
    
    return res # ugly, but clear?

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

# Bounds inference with vectorized semantics would *mostly* just propagate bounds back to start, then pull forward. Main issue are update stages where the RDom also influences the bounds.
# Maybe this is manageable with some non-crazy rewrites in the decorator?
#   What would a bounds protocol compatible version of the histogram or cdf look like?
#   It would have the computed interval set on the init, and the result sliced out to return


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
