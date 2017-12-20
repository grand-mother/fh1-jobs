#!/usr/bin/env python
import fnmatch
import os

from irods.exception import CollectionDoesNotExist
from irods.session import iRODSSession


HOME = "/trend/home/trirods"


def Connection():
    """Closure encapsulating an irods connection
    """
    environment = os.path.expanduser("~/.irods/irods_environment.json")
    collection = [None, ]

    def cd(session, *args):
        """List the current subcollections
        """
        if not args:
            path = HOME
        elif args[0].startswith("/"):
            path = args[0]
        else:
            path = os.path.join(collection[0].path, args[0])
            path = os.path.normpath(path)
        try:
            collection[0] = session.collections.get(path)
        except CollectionDoesNotExist:
            print "... path `{:}` does not exist".format(args[0])

    def ls(session, *args):
        """List the current subcollections
        """
        if not args:
            args = ("*",)

        for iteration, pattern in enumerate(args):
            # Find items that match the pattern
            content = {}
            for c in collection[0].subcollections:
                if fnmatch.fnmatch(c.name, pattern):
                    content[c.name] = c
            for d in collection[0].data_objects:
                if fnmatch.fnmatch(d.name, pattern):
                    content[d.name] = d

            # Print the result
            if iteration > 0:
                print ""
            if len(args) > 1:
                print "{:}:".format(pattern)
            print sorted(content.keys())

    # Map the commands to valid names
    action = {"ls": ls, "cd": cd}

    def connect():
        """Connect to an irods server
        """
        with iRODSSession(irods_env_file=environment) as session:
            # Fetch the home collection
            cd(session)

            # Main loop over commands
            while True:
                current_dir = os.path.split(collection[0].path)[1]
                print "[trirods@ccirods {:}]$".format(current_dir),
                try:
                    args = raw_input().split()
                    try:
                        command = action[args[0]]
                    except KeyError:
                        print "... unknown command `{:}`".format(args[0])
                        continue
                    command(session, *args[1:])
                except KeyboardInterrupt:
                    print ""
                    continue
                except (EOFError, SystemExit):
                    print ""
                    break

    return connect


if __name__ == "__main__":
    connect = Connection()
    connect()
