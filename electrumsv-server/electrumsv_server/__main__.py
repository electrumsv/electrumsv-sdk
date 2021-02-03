import sys

from . import application

try:
    application.run()
except KeyboardInterrupt:
    sys.exit(0)

