#!/usr/bin/env python
import getpass
import os
import stat
import sys

from irods.password_obfuscation import encode


# Read the password from the command line
try:
    password = getpass.getpass("Enter irods password:")
    confirm = getpass.getpass("Confirm password:")
except KeyboardInterrupt:
    print "^C"
    sys.exit(0)
except EOFError:
    print "^D"
    sys.exit(0)
if password != confirm:
    raise ValueError("confirmation does not match")


# Encode and dump the password
path = os.path.expanduser("~/.irods")
if not os.path.exists(path):
    os.makedirs(path)

path = os.path.join(path, ".irodsA")
uid = os.getuid()
with open(path, "wb+") as f:
    f.write(encode(password))
os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
print "Irods password has been set"
