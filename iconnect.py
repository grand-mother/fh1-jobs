#!/usr/bin/env python
import cmd
import fnmatch
import shlex
import os
import subprocess

from irods.exception import CollectionDoesNotExist
from irods.session import iRODSSession


HOME = "/trend/home/trirods"


class Connection(cmd.Cmd, object):
    """Command processor for an irods connection
    """

    sesssion = None

    cursor = None

    def default(self, line):
        """Handle unknown commands
        """
        args = shlex.split(line)
        print "... unknown command `{:}`".format(args[0])

    def do_cd(self, line):
        """Change the current irods collection
        """
        # Parse the new path
        args = shlex.split(line)
        if not args:
            path = HOME
        elif args[0].startswith("/"):
            path = args[0]
        else:
            path = os.path.join(self.cursor.path, args[0])
            path = os.path.normpath(path)

        # Fetch the corresponding irods collection
        try:
            self.cursor = self.session.collections.get(path)
        except CollectionDoesNotExist:
            print "... path `{:}` does not exist".format(args[0])
        else:
            # Update the prompt
            current = os.path.split(self.cursor.path)[1]
            self.prompt = "[trirods@ccirods {:}]$ ".format(current)

    def do_ls(self, line):
        """List the objects inside the current irods collection
        """
        args = shlex.split(line)
        if not args:
            args = ("*",)

        for iteration, pattern in enumerate(args):
            # Find items that match the pattern
            content = {}
            for c in self.cursor.subcollections:
                if fnmatch.fnmatch(c.name, pattern):
                    content[c.name] = c
            for d in self.cursor.data_objects:
                if fnmatch.fnmatch(d.name, pattern):
                    content[d.name] = d

            # Print the result
            if iteration > 0:
                print ""
            if len(args) > 1:
                print "{:}:".format(pattern)
            print sorted(content.keys())

    def do_shell(self, line):
        args = shlex.split(line)
        if args and (args[0] == "cd"):
            os.chdir(args[1])
        else:
            p = subprocess.Popen(line, shell=True)
            p.communicate()

    def do_EOF(self, line):
        print ""
        return True

    def cmdloop(self, intro=None):
        """Override the default command loop in order to catch Ctrl+C
        """
        environment = os.path.expanduser("~/.irods/irods_environment.json")
        with iRODSSession(irods_env_file=environment) as self.session:
            self.do_cd("")

            while True:
                try:
                    super(Connection, self).cmdloop(intro="")
                    break
                except KeyboardInterrupt:
                    print("^C")


if __name__ == '__main__':
    Connection().cmdloop()
