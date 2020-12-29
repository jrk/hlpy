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