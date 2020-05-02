import sys
from json import (dump as json_dump)
import click
from typing import List
from . import process_elf


@click.command(name='lddcollect')
@click.option('--dpkg/--no-dpkg', default=False, help="Lookup dpkg libs or not, default: no")
@click.option('--json', is_flag=True, help="Output in json format")
@click.option('--verbose', is_flag=True, help="Print some info to stderr")
@click.argument('libs',
                nargs=-1,
                type=click.Path(exists=True, dir_okay=False, file_okay=True))
def main(libs: List[str],
         dpkg: bool = False,
         json: bool = False,
         verbose: bool =False):
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

    pkgs, files, missing = process_elf(libs, verbose=verbose, dpkg=dpkg)

    files = sorted(files)
    pkgs = sorted(pkgs) if dpkg else None

    if json:
        out = {'files': files}
        if pkgs is not None:
            out['packages'] = pkgs
        json_dump(out, sys.stdout, indent=2)
    else:
        for file in files:
            print(file)

        if pkgs is not None:
            print("...")
            for pkg in pkgs:
                print(pkg)

    if len(missing) > 0:
        sys.stdout.flush()
        print(f"\nThere were missing libraries", file=sys.stderr)
        for lib in missing:
            print(f"   {lib}", file=sys.stderr)
        sys.exit(1)

main()
