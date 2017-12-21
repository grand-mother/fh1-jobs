#!/usr/bin/env python
import cmd
import fnmatch
import getopt
import shlex
import os
import subprocess

from irods.exception import (CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME,
                             CAT_NAME_EXISTS_AS_COLLECTION,
                             CollectionDoesNotExist, DataObjectDoesNotExist,
                             USER_FILE_DOES_NOT_EXIST)
from irods.session import iRODSSession
from irods.data_object import irods_basename


HOME = "/trend/home/trirods/grand"


class Connection(cmd.Cmd, object):
    """Command processor for an irods connection
    """

    sesssion = None

    cursor = None

    class _ConnectionError(Exception):
        pass

    def default(self, line):
        """Handle unknown commands
        """
        args = shlex.split(line)
        self.println("... unknown command `{:}`", args[0])

    def get_content(self, pattern, data=True, collections=True):
        """Get items within the collection that match the pattern
        """
        content = {}
        if collections:
            for c in self.cursor.subcollections:
                if fnmatch.fnmatch(c.name, pattern):
                    content[c.name] = c
        if data:
            for d in self.cursor.data_objects:
                if fnmatch.fnmatch(d.name, pattern):
                    content[d.name] = d
        return content

    def get_path(self, path):
        if path.startswith("/"):
            return path
        else:
            path = os.path.join(self.cursor.path, path)
            return os.path.normpath(path)

    def parse_command(self, command, options, line, noargs=False):
        """Parse a command line for arguments and options
        """
        args = shlex.split(line)
        try:
            opts, args = getopt.getopt(args, options)
        except getopt.GetoptError as e:
            self.println("... {:}: {:}", command, e.msg)
            raise self._ConnectionError()

        if (not noargs) and (not args):
            self.println("... {:}: missing operand", command)
            raise self._ConnectionError()
        return opts, args

    def println(self, text, *opts):
        self.printfmt(text, *opts)
        print

    def printfmt(self, text, *opts):
        if opts:
            text = text.format(*opts)
        else:
            text = str(text)
        print self.prompt + text,

    def ask_for_confirmation(self, text, *args):
        self.printfmt(text, *args)
        try:
            answer = raw_input()
        except EOFError:
            return False
        if answer in ("y", "Y", "yes", "Yes"):
            return True
        return False

    def do_cd(self, line):
        """Change the current irods collection
        """
        # Parse the new path
        try:
            opts, args = self.parse_command("cd", "", line, noargs=True)
        except self._ConnectionError:
            return
        if not args:
            path = HOME
        else:
            path = self.get_path(args[0])

        # Fetch the corresponding irods collection
        try:
            self.cursor = self.session.collections.get(path)
        except CollectionDoesNotExist:
            self.println("... path `{:}` does not exist", args[0])
        else:
            # Update the prompt
            current = irods_basename(self.cursor.path)
            self.prompt = "[trirods@ccirods {:}]$ ".format(current)

    def complete_cd(self, text, line, begidx, endidx):
        return self.get_content(text + "*", data=False).keys()

    def do_ls(self, line):
        """List the objects inside the current irods collection
        """
        try:
            opts, args = self.parse_command("ls", "", line, noargs=True)
        except self._ConnectionError:
            return
        if not args:
            args = ("*",)

        for iteration, pattern in enumerate(args):
            # Find items that match the pattern
            content = self.get_content(pattern)

            # Print the result
            if iteration > 0:
                self.println("")
            if len(args) > 1:
                self.println("{:}:", pattern)
            self.println(sorted(content.keys()))

    def complete_ls(self, text, line, begidx, endidx):
        return self.get_content(text + "*").keys()

    def do_mkdir(self, line):
        try:
            opts, args = self.parse_command("mkdir", "", line)
        except self._ConnectionError:
            return

        for arg in args:
            path = self.get_path(arg)
            try:
                self.session.collections.create(path)
            except CATALOG_ALREADY_HAS_ITEM_BY_THAT_NAME:
                self.println("... mkdir: cannot create collection `{:}`:"
                             " Object exists", irods_basename(path))
                break

    def complete_mkdir(self, text, line, begidx, endidx):
        return self.get_content(text + "*").keys()

    def do_pwd(self, line):
        self.println(self.cursor.path)

    def do_rm(self, line):
        try:
            opts, args = self.parse_command("rm", "rfT", line)
        except self._ConnectionError:
            return

        protect_collections = True
        request_confirmation = True
        skip_trash = False
        for opt, param in opts:
            if opt == "-r":
                protect_collections = False
            elif opt == "-f":
                request_confirmation = False
            elif opt == "-T":
                skip_trash=True

        for arg in args:
            # Check that the object exist and what is its type
            path = self.get_path(arg)
            basename = irods_basename(path)
            try:
                target = self.session.data_objects.get(path)
            except DataObjectDoesNotExist:
                try:
                    target = self.session.collections.get(path)
                except CollectionDoesNotExist:
                    self.println("... rm: cannot remove object `{:}`:"
                                 "No such data or collection", basename)
                    return
                else:
                    itype = "collection"
            else:
                itype = "data object"

            # Check for the recursive mode
            if protect_collections and (itype == "collection"):
                self.println("... rm: cannot remove `{:}`: Is a collection",
                             basename)
                return

            # Check for a confirmation
            if request_confirmation:
                if not self.ask_for_confirmation(
                    "rm: remove {:} `{:}'?", itype, basename):
                    continue

            # Now we can remove the data
            try:
                if itype == "collection":
                    self.session.collections.remove(path)
                else:
                    self.session.data_objects.unlink(path, force=skip_trash)
            except USER_FILE_DOES_NOT_EXIST:
                self.println("... rm: cannot remove object `{:}`:"
                             "No such data or collection", basename)
                return

    def complete_rm(self, text, line, begidx, endidx):
        return self.get_content(text + "*").keys()

    def do_put(self, line):
        try:
            opts, args = self.parse_command("put", "rf", line)
        except self._ConnectionError:
            return

        recursive = False
        request_confirmation = True
        for opt, param in opts:
            if opt == "-r":
                recursive = True
            elif opt == "-f":
                request_confirmation = False

        # Parse the src(s) and the destination
        if len(args) == 1:
            srcs = args
            dst = self.cursor.path
        else:
            if len(args) == 2:
                srcs = (args[0],)
            else:
                srcs = args[:-1]
            dst = self.get_path(args[-1])

        # Check if the destination is an existing collection
        if self.session.collections.exists(dst):
            if not dst.endswith("/"):
                dst += "/"
        elif len(srcs) > 1:
            self.println("... put: target `{:}` is not a directory", basename)
            return

        # Upload the data
        def upload(srcs, dst):
            for src in srcs:
                basename = os.path.basename(src)
                if dst.endswith("/"):
                    target = dst + basename
                else:
                    target = dst

                if os.path.isdir(src):
                    if not recursive:
                        self.println("... put: omitting collection `{:}`",
                                     basname)
                        raise self._ConnectionError()
                    if not self.session.collections.exists(target):
                        self.session.collections.create(target)
                    children = [os.path.join(src, f) for f in os.listdir(src)]
                    upload(children, target + "/")
                else:
                    if self.session.data_objects.exists(target):
                        if request_confirmation:
                            if not self.ask_for_confirmation(
                                "put: overwrite data object `{:}'?", basename):
                                continue
                    try:
                        self.session.data_objects.put(src, dst)
                    except CAT_NAME_EXISTS_AS_COLLECTION:
                        self.println("... put: `{:}` is an existing collection",
                                     basename)
                        raise self._ConnectionError()
        try:
            upload(srcs, dst)
        except self._ConnectionError:
            return

    def complete_put(self, text, line, begidx, endidx):
        try:
            opts, args = self.parse_command("put", "rf", line[3:], noargs=True)
        except self._ConnectionError:
            return []
        pattern = text + "*"
        nargs = len(args)
        if (nargs < 1) or ((nargs == 1) and (line[-1] != " ")):
            return filter(lambda s:fnmatch.fnmatch(s, pattern), os.listdir("."))
        else:
            return self.get_content(pattern).keys()

    def do_shell(self, line):
        args = shlex.split(line)
        if args and (args[0] == "cd"):
            os.chdir(args[1])
        else:
            p = subprocess.Popen(line, shell=True)
            p.communicate()

    def do_EOF(self, line):
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
            print


if __name__ == '__main__':
    Connection().cmdloop()
