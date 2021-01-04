# -*- coding: utf-8 -*-
# %% [markdown]
# Playing around with an alternate, Python AST-based embedding of Halide.

# %% [markdown]
# This is exploratory _sketching_, and not internally consistent — it is meant to
# be toying with different possible syntax ideas in different places.
#
# It is mostly *linear*, and can be roughly read top-to-bottom as a progression of ideas.

# %% [markdown]
# # A first cut
#
# Assume the existence of some core Halide decorators and types:
# %%
def _nop(*args, **kwargs): pass
func = pure = update = pipe = var = _nop
Buffer = UInt = Int = Float = _nop

# %% [markdown]
# ## Pure Funcs
# Raw and simple:

# %%
inp = Buffer(UInt(16), 2)

@func
def blur_x(x, y):
    return (inp(x-1, y) + inp(x, y) + inp(x+1, y)) / 3

@func
def blur_y(x, y):
    return (blur_x(x-1, y) + blur_x(x, y) + blur_x(x+1, y)) / 3


# %% [markdown]
# Pure funcs are actually just sensible (if slow) Python.
#
# Is it possible to interpret these with a vectorized semantics where they also
# take *intervals* for the dimensions, and return arrays?

# %% [markdown]
# ## Semantics
# I quickly found myself drawn into the idea that this should also be able to
# have a simple semantics defined in terms of regular Python, without too many
# rewrites implied by the decorators, if you allow `Var` arguments to take
# vectors or ranges as well as scalar values. I was imagining that a simple
# interpreter based on pushing through NumPy arrays would just work with fairly
# modest translation of the AST that Python-fluent programmers could easily learn
# and understand. I'm not sure whether this is actually a good idea to prioritize.

# %% [markdown]
# ## Update stages
# What about update stages?

# %%
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


# %% [markdown]
# This seems potentially confusing.
#
# - Do we close over the x,y of the parent?
# - Do the vectorized semantics properly carry over?

# %% [markdown]
# ### What about a histogram & scan?
# %%
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
                res[inp(x,y)] += 1
                # It *has* to be array index, because Python won't parse an
                # assign to a call!

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


# %% [markdown]
# Bounds inference with vectorized semantics would *mostly* just propagate bounds
# back to start, then pull forward. Main issue are update stages where the RDom
# also influences the bounds.
#
# Maybe this is manageable with some non-crazy rewrites in the decorator? What
# would a bounds protocol compatible version of the histogram or cdf look like?
# => It would have the computed interval set on the init, and the result sliced
# out to return.
#
# For the vectorized semantics to work without some vector calls in the return
# statement, this would probably have to be rewritten in the decorator to
# implicitly allocate the return buffer over x,y, then populate and return that:

# %%
@func
def test(x,y):
    return 0 # would not generate a vector, even if x,y were vectors

def test_transformed(x, y):
    res = alloc(x,y)
    res[x,y] = 0
    return res


# %% [markdown]
# - [ ] **TODO:** Are generators just functions which locally define and return Funcs?
# - [ ] **TODO:** Try porting all of an app to see how it looks

# %% [markdown]
# # Alternates
#
# These are parameterized over inputs. Properly general, but verbose, and doesn't
# correspond to actual Halide

# %%
def blur_x(x : var, y : var, inp : func):
    return (inp(x-1, y) + inp(x, y) + inp(x+1, y))/3

def blur_y(x : var, y : var, bx : func):
    return (bx(x, y-1) + bx(x, y) + bx(x, y+1))/3


# %% [markdown]
# - [ ] **TODO:** What about return types? Consider setting / checking them?

# %% [markdown]
# # Revision 2
# ## Stripped down update stage syntax
#
#   - If it's a multi-stage func, we don't need decorators inside. It should all
#     be defs, with the first a pure init, and the rest updates taking a result
#     buffer.
#
#   - Inner stage definitions DO NOT take Var arguments. They have to close over
#     the vars of the parent. If the since those are the only dims which are
#     actually available. Paired with a simple syntactic rule that a multi-stage
#     func can ONLY contain a list of `def`s and no other statements, this should
#     syntactically (roughly) enforce a clear model of what is semantically
#     possible.
#
#   - Maybe the semantics aren't that bad? They hopefully just correspond to the
#     decorator implying that you add a final line to return the result of
#     applying each of the stages in order:
#     
#       ```
#       return upd2(upd1(init())) # still implicitly closed over x,y
#       ```
#     
#     For bounds inference of RDoms to work, this probably also requires that
#     init() first be extended to take explicit bounds, which are also computed
#     and inserted from all the update steps.
#     
#   - Inits to 0 can be omitted?

# %%
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


# %% [markdown]
# Simple blur:
# %%
@func
def blur(x, y):
    def init():
        return 0
    
    def upd(res):
        for i in seq(-1,1):
            for j in seq(-1,1):
                res[x,y] += inp(x+i, y+j)
# %% [markdown]
# - [ ] Should res have to be indexed in this case? Is there a difference between
#   that, and allowing a scalar res (or one that's pure along some dimensions but
#   not others)?

# %% [markdown]
# A few tweaked alternatives:
# %%
@func
def blur(x, y):
    # Consider: Init expr as default res argument to first update?
    # def upd(res = 0), or:
    def upd(res = zeros(x,y)):
        for i in seq(-1,1):
            for j in seq(-1,1):
                res[x,y] += inp(x+i, y+j)


# %%
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
# %% [markdown]
# I don't think that was effective.

# %% [markdown]
# This is starting to feel decent:
# %%
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
            res[x, flip_ry] = (1 - alpha) * res[x, flip_ry + 1] \
                                  + alpha * res[x, flip_ry]


# %% [markdown]
# # How will we represent schedules?
# My initial thought was that you'd be able to just reach in and grab update
# stages by field reference chaining, like `iir_blur.init_top`. But I realize
# this only addresses func/stage references, and doesn't cover how to name the
# Vars or RVars.
#
# A more explicit model would have you do like `blur.upd.i` or `blur_x.x`. (The
# `@func` decorator would always translate the function into an object that had
# these members populated.)
#
# Maybe the verbosity of the more explicit model of having vars associated with
# their function definition actually makes things clearer? It's often unclear to
# new users which `x` you're even referring to when you use a Var in a complex
# scheduling statement (especially one involving multiple Funcs like `compute_at`)
#
# An extreme other end would be to just let you use strings and match those with
# the names in the definitions: you'd use `'x'` instead of `blur_x.x`.
#
# Maybe we support both of these?  
# Is the more explicit form encouraged?  
# Are strings automatically translated into the more explicit form?
#
# One notable thing with the explicit form: `compute_at` and `store_at` would
# need only a single argument, not two, as `f.compute_at(g.x)` is unambiguous.

# %% [markdown]
# # Nesting
# One thought: this syntax seems to naturally lend itself to nesting pipelines
# within Funcs.

# %%
@func
def parent(x,y):
    @func
    def child1(x,y):
        return x+y
    
    @func
    def child2(x,y):
        return child1(x-1,y) + child1(x,y)
    
    return child2(x*2,y*2)


# %% [markdown]
# This variant feels awkward, as it doesn't really make the sub-pipeline a
# separate thing, which could be applied multiple times. This really seems to
# require [lambda abstraction](#Lambda-Abstraction) of the child pipeline to make
# sense.

# %% [markdown]
# # Lambda Abstraction
# ...would amount to allowing Func definitions and calls to take params other
# than just Vars.
#
# The types of params would be the same as those allowed in Generators.  
# Would they also have Input and Output desigations, and default values?
#
# How do you abstract over multi-output `Pipeline`s?
#
# This is also a question for the core Halide IR and language, as much as it is
# for this new embedding. But this embedding could presumably add lambda
# abstraction, with basic restrictions (no recursion), and entirely de-sugar
# applications of lambdas into a flattened program (or maybe a C++ Generator?) in
# the front-end for now.
#
# ***
#
# There is a strong correspondence between lambda abstraction and Generators. A
# Generator (or the subset which is maps params to a pipeline) really is our
# lambda.
#
# If we could just make the syntax way more obvious and concise, is this all we
# need? Perhaps a simple `@pipeline` _is_ the unit of lambda abstraction?

# %%
# where do the dimensions go?
# What about multiple outputs, with different dimensionality?
# Multiple outputs can just be a tuple of @funcs returned from the @pipe.
@pipe
def my_first_generator(offset : UInt(8), input : Buffer(UInt(8), 2)):
    @func
    def brighter(x,y):
        return input(x,y) + offset
    
    # Schedule here? Or def schedule()?
    
    return brighter

# %% [markdown]
# Can we define a pyramid constructor that re-uses the same subroutine logic at
# every level as a nested pair of pipelines?

# %% [markdown]
# ***
# # Pending Ideas & Questions
# - [ ] With the nesting of function definitions to create multi-stage Funcs and
#   Pipelines/generators, should we consider a **class**-based top-level
#   structure, instead of a **function**-based one?
#     - What are the syntacting objects to which decorators can be applied? Any
#       besides `def` and `class`?
# - [ ] What about inline reduction helpers?
#     - How do they carry over?
#         - Just pass through to the C++ syntax stupidly? Is that feasible?
#         - What about if we try to dump out as serialized IR — they don't exist
#           then?
#     - Could you implement them nicely in this syntax?
#         - Can you have a scalar intermediate that's just used within the loops
#           of an update, and then assigned to `res[x,y]`
# - [ ] Are there loops other than `seq`? Can there be a `par` loop, and what
#   would it mean?
