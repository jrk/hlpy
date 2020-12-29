Playing around with an alternate, Python AST-based embedding of Halide.

I quickly found myself drawn into the idea that this should also be able to have a simple semantics defined in terms of regular Python, without too many rewrites implied by the decorators, if you allow Var arguments to take vectors or ranges as well as scalar values. I was imagining that a simple interpreter based on pushing through NumPy arrays would just work with fairly modest translation of the AST that Python-fluent programmers could easily learn and understand. I'm not sure whether this is actually a good idea to prioritize.

The current [sketching.py](sketching.py) is also inconsistent, as I toy with slightly different possible syntax ideas in different places.

# How will we represent schedules?
My initial thought was that you'd be able to just reach in and grab update stages by field reference chaining, like `iir_blur.init_top`. But I realize this only addresses func/stage references, and doesn't cover how to name the Vars or RVars.

A more explicit model would have you do like `blur.upd.i` or `blur_x.x`. (The `@func` decorator would always translate the function into an object that had these members populated.)

Maybe the verbosity of the more explicit model of having vars associated with their function definition actually makes things clearer? It's often unclear to new users which `x` you're even referring to when you use a Var in a complex scheduling statement (especially one involving multiple Funcs like `compute_at`)

An extreme other end would be to just let you use strings and match those with the names in the definitions: you'd use `'x'` instead of `blur_x.x`.

Maybe we support both of these?
Is the more explicit form encouraged?
Are strings automatically translated into the more explicit form?

One notable thing with the explicit form: `compute_at` and `store_at` would need only a single argument, not two, as `f.compute_at(g.x)` is unambiguous.

# Nesting
One thought: this syntax seems to naturally lend itself to nesting pipelines within Funcs.

```python
@func
def parent(x,y):
    @func
    def child1(x,y):
        return x+y
    
    @func
    def child2(x,y):
        return child1(x-1,y) + child1(x,y)
    
    return child2(x*2,y*2)
```

This variant feels awkward, as it doesn't really make the sub-pipeline a separate thing, which could be applied multiple times. This really seems to require [lambda abstraction](#Lambda-Abstraction) of the child pipeline to make sense.

# Lambda Abstraction
...would amount to allowing Func definitions and calls to take params other than just Vars.

The types of params would be the same as those allowed in Generators.
Would they also have Input and Output desigations, and default values?

How do you abstract over multi-output `Pipeline`s?

This is also a question for the core Halide IR and language, as much as it is for this new embedding. But this embedding could probably add lambda abstraction, with basic restrictions (no recursion), and entirely de-sugar it into a flattened program (or maybe a C++ Generator?) in the front-end.

There is a strong correspondence between lambda abstraction and Generators. A Generator (or the subset which is maps params to a pipeline) really is our lambda.

If we could just make the syntax way more obvious and concise, is this all we need? Perhaps a simple `@pipeline` _is_ the unit of lambda abstraction?

```python
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
```

Can we define a pyramid constructor that re-uses the same subroutine logic at every level as a nested pair of pipelines?