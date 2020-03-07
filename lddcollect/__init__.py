""" Tools for listing files needed to run elf executable to use elf library.
"""
from auditwheel.lddtree import lddtree
import subprocess


def dpkg_s(*args):
    """ Call `dpkg -S {arg}` and parse output into a list of tuples:

        [(pkg-name, full-path)]

        Returns
        =======
        [(pkg, path),...], [not-found-inputs]
    """
    def parse_line(l):
        ii = l.find(': ')
        if ii < 0:
            raise ValueError('Unexpected output from dpkg')
        deb, path = l[:ii], l[ii+2:]

        return (deb, path)

    proc = subprocess.Popen(['/usr/bin/dpkg', '-S', *args],
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE)

    exit_code = proc.wait()
    lines = proc.stdout.read().decode('utf8').split('\n')
    parsed = [parse_line(l) for l in lines if l]
    missing = []
    if exit_code != 0:
        for a in args:
            if not any(a in path for _,path in parsed):
                missing.append(a)

    return parsed, missing
