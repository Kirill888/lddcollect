lddcollect
==========

List all shared library files needed to run ELF executable or load elf library.
On Debian based systems can also list packages needed instead of library files.

Typical use case: you have a locally compiled application or library with large
number of dependencies, and you want to share this binary. This tool will list
all shared libraries needed to run it. You can then create a minimal rootfs with
just the needed libraries. Alternatively you might want to know what packages
need to be installed to run this application (Debian based systems only for
now).

Installation
============

This tool is Python (3.6+) based. It can be installed with ``pip``:

::
  pip3 install lddcollect


Usage
=====

::
   python3 -m lddcollect --help
   Usage: __main__.py [OPTIONS] [LIBS]...

     Find all other libraries and optionally Debian dependencies listed
     applications/libraries require to run.

     Prints libraries (including symlinks) that are referenced by input files,
     one file per line.

     When --dpkg option is supplied, print:

       1. Non-dpkg managed files, one per line
       2. Separator line: ...
       3. Package names, one per line

   Options:
     --dpkg / --no-dpkg  Lookup dpkg libs or not, default: no
     --json              Output in json format
     --verbose           Print some info to stderr
     --help              Show this message and exit.

There are two modes of operation.

1. List all shared library files needed to execute supplied inputs
2. List all packages you need to ``apt-get install`` to execute supplied inputs
   as well as any shared libraries that are needed but are not under package
   management.

In the first mode it is similar to ``ldd``, except referenced symbolic links to
libraries are also listed. In the second mode shared library dependencies that
are under package management are not listed, instead the name of the package
providing the dependency is listed.
