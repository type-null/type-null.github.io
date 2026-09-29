# Superseded development utility

`serve.py` is the earlier HTTP preview helper, retained as source history. It is no longer part of the publishing workflow: the generated website can be opened directly from `index.html`, and the build creates the deployment artifact separately.

The script imports the builder from its original sibling location. To reuse this optional developer utility, copy it back to `scripts/serve.py` before running it. No server is needed to read the generated local website.
