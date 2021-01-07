# Sketching
Playing around with an alternate, Python AST-based embedding of Halide.

Check out the [markdown](sketching.md) first as the most readable form.
(Also rendered in parallel as [python source](sketching.py) and a [jupyter notebook](sketching.ipynb). I'm using [jupytext](https://jupytext.readthedocs.io) to sync them, and actually find working in markdown much of the time most effective.)

# Development
Set up to use [pipenv](https://pipenv.pypa.io/en/latest/) and [pyenv](https://github.com/pyenv/pyenv). (I also use [direnv](https://direnv.net) so I don't have to manually switch to and from the `pipenv shell`, but that's optional.) To get started:

```bash
$ git clone git@github.com:jrk/hlpy.git
$ cd hlpy
$ pipenv install # bootstrap the environment
$ pipenv shell # enter the environment, if not using direnv
```

# TODO
- [x] Start project template
- [ ] Define IR for front-end
    - Use dataclass
    - Do we *also* want to inherit from `ast.AST` to enable `ast.NodeVisitor` traversal, or should we make our own visitor scheme?
        - Turns out [it's trivial](https://github.com/python/cpython/blob/master/Lib/ast.py#L386), and we can easily roll our own
- [ ] Start parsing AST
