import os

env = os.environ.get("DJANGO_ENV", "local")

if env == "render":
    from .render import *
else:
    from .local import *
