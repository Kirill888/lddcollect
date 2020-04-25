import sys
from json import (dump as json_dump)
import click
from . import process_elf


@click.command(name='lddcollect')
@click.option('--dpkg/--no-dpkg', default=False, help="Lookup dpkg libs or not, default: no")
@click.option('--json', is_flag=True, help="Output in json format")
@click.option('--verbose', is_flag=True, help="Print some info to stderr")
@click.argument('libs',
                nargs=-1,
                type=click.Path(exists=True, dir_okay=False, file_okay=True))
def main(libs, dpkg=False, json=False, verbose=False):
    """Find all other libraries and optionally Debian dependencies listed
    applications/libraries require to run.

    Prints libraries (including symlinks) that are referenced by input files, one
    file per line.

    When --dpkg option is supplied, print:

    \b
      1. Non-dpkg managed files, one per line
      2. Separator line: ...
      3. Package names, one per line

    """

    debs = set()
    files = set()
    missing = []

    for lib in libs:
        _debs, _files, _missing = process_elf(lib, verbose=verbose, dpkg=dpkg)
        debs.update(_debs)
        files.update(_files)
        missing.extend(_missing)

    files = sorted(files)
    debs = sorted(debs) if dpkg else None

    if json:
        out = {'files': files}
        if debs is not None:
            out['debs'] = debs
        json_dump(out, sys.stdout, indent=2)
    else:
        for file in files:
            print(file)

        if debs is not None:
            print("...")
            for deb in debs:
                print(deb)

    if len(missing) > 0:
        print(f"There were missing libraries", file=sys.stderr)
        for lib in missing:
            print(f"   {lib}", file=sys.stderr)

main()
