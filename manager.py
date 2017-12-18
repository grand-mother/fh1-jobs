#!/usr/bin/env python
#
# -----------------------------------------
# Scheduler options
# -----------------------------------------
#MSUB -N beanstalkd
#MSUB -q develop
#MSUB -l nodes=1:ppn=1
#MSUB -l walltime=300
#MSUB -l pmem=1gb
#MSUB -v PATH, PYTHONPATH
# -----------------------------------------

import json
import os
import socket
import subprocess
import time


class Deamon:
    """Encapsulation of a beanstalk deamon
    """

    def __init__(self):
        """Spawn a beanstalk deamon on an unused port
        """
        # Reserve an unused port
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind(("0.0.0.0", 0))
        _, port = s.getsockname()
        del s


        # Dump the address
        if ((not os.path.exists("share")) or
            (not os.path.exists("share/binlog"))):
            os.makedirs("share/binlog")

        self._address = socket.gethostname(), port
        with open("share/beanstalkd-address.json", "w+") as f:
            json.dump(self._address, f)


        # Spawn the beanstalk deamon
        cmd = "beanstalkd -p {:} -b share/binlog".format(
            self._address[1])
        self._process = subprocess.Popen(cmd, shell=True)

    def __del__(self):
        """Kill the deamon process
        """
        self._process.kill()

    @property
    def address(self):
        """The address to which the deamon is bound
        """ 
        return self._address


def feed(deamon, buffer=10):
    """Feed the queue with jobs
    """

    time.sleep(3.)


if __name__ == "__main__":
    feed(Deamon())  
