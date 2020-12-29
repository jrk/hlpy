Playing around with an alternate, Python AST-based embedding of Halide.

I quickly found myself drawn into the idea that this should also be able to have a simple semantics defined in terms of regular Python, without too many rewrites implied by the decorators, if you allow Var arguments to take vectors or ranges as well as scalar values. I was imagining that a simple interpreter based on pushing through NumPy arrays would just work with fairly modest translation of the AST that Python-fluent programmers could easily learn and understand. I'm not sure whether this is actually a good idea to prioritize.

The current [sketching.py](sketching.py) is also inconsistent, as I toy with slightly different possible syntax ideas in different places.