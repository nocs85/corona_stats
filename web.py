# The primary purpose of this module is to carefully patch, in place, portions
# of the standard library with gevent-friendly functions that behave in the same
# way as the original (at least as closely as possible).
from gevent import monkey
monkey.patch_all()

# flask application import
from app import app