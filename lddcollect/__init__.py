""" Tools for listing files needed to run elf executable to use elf library.
"""
import subprocess
import itertools
from queue import Queue
from auditwheel.lddtree import lddtree


def dpkg_s(*args):
    """ Call `dpkg -S {arg}` and parse output into a list of tuples:

        [(pkg-name, full-path)]

        Returns
        =======
        [(pkg, path),...], [not-found-inputs]
    """
    def parse_line(line):
        idx = line.find(': ')
        if idx < 0:
            raise ValueError('Unexpected output from dpkg')
        deb, path = line[:idx], line[idx + 2:]
        return (deb, path)

    proc = subprocess.Popen(['/usr/bin/dpkg', '-S', *args],
                            stderr=subprocess.PIPE,
                            stdout=subprocess.PIPE)

    exit_code = proc.wait()
    lines = proc.stdout.read().decode('utf8').split('\n')
    parsed = [parse_line(l) for l in lines if l]
    missing = []
    if exit_code != 0:
        for arg in args:
            if not any(arg in path for _, path in parsed):
                missing.append(arg)

    return parsed, missing


def _paths(ltree):
    for lib in itertools.chain(iter([ltree]), ltree['libs'].values()):
        path, realpath = lib['path'], lib['realpath']
        yield path
        if path != realpath:
            yield realpath


def process_elf(fname):
    """Find dependencies for a given elf file.

    Returns:

      List of debian package names supplied file or it's non-dpkg dependants
      reference and a list of files that are not managed by dpkg.

      [debs], [files]

    """
    print(f"Finding dependencies ({fname})")
    ltree = lddtree(fname)
    libs = ltree['libs']
    all_libs = list(_paths(ltree))

    print(f"Querying dpkg for files ({len(all_libs)})")
    debs, non_deb = dpkg_s(*all_libs)

    libpath2deb = {path: deb for deb, path in debs}
    lib2deb = {
        n: libpath2deb.get(lib['path'], None)
        for n, lib in libs.items()
    }
    lib2deb[fname] = libpath2deb.get(ltree['path'], None)

    seen = set()
    debs = set()
    files = set()

    q = Queue()
    q.put((fname, ltree))

    while not q.empty():
        name, lib = q.get()
        if name in seen:
            continue

        seen.add(name)
        deb = lib2deb.get(name, None)
        if deb is not None:
            debs.add(deb)
            continue
        else:
            files.add(lib['path'])
            files.add(lib['realpath'])

        for name in lib['needed']:
            if name not in seen:
                q.put((name, libs[name]))

    return list(debs), list(files)
