#-*- coding: ISO-8859-1 -*-
# setup.py: the distutils script
#
# Copyright (C) 2004-2007 Gerhard H�ring <gh@ghaering.de>
#
# This file is part of pysqlite.
#
# This software is provided 'as-is', without any express or implied
# warranty.  In no event will the authors be held liable for any damages
# arising from the use of this software.
#
# Permission is granted to anyone to use this software for any purpose,
# including commercial applications, and to alter it and redistribute it
# freely, subject to the following restrictions:
#
# 1. The origin of this software must not be misrepresented; you must not
#    claim that you wrote the original software. If you use this software
#    in a product, an acknowledgment in the product documentation would be
#    appreciated but is not required.
# 2. Altered source versions must be plainly marked as such, and must not be
#    misrepresented as being the original software.
# 3. This notice may not be removed or altered from any source distribution.

import glob, os, re, sys
import urllib
import zipfile

from setuptools import setup, Extension, Command
from setuptools.command.build_ext import build_ext

import cross_bdist_wininst

# If you need to change anything, it should be enough to change setup.cfg.

sqlite = "sqlite"

PYSQLITE_EXPERIMENTAL = False

sources = ["src/module.c", "src/connection.c", "src/cursor.c", "src/cache.c",
           "src/microprotocols.c", "src/prepare_protocol.c", "src/statement.c",
           "src/util.c", "src/row.c"]

if PYSQLITE_EXPERIMENTAL:
    sources.append("src/backup.c")

include_dirs = []
library_dirs = []
libraries = []
runtime_library_dirs = []
extra_objects = []
define_macros = []

long_description = \
"""Python interface to SQLite 3

pysqlite is an interface to the SQLite 3.x embedded relational database engine.
It is almost fully compliant with the Python database API version 2.0 also
exposes the unique features of SQLite."""

if sys.platform != "win32":
    define_macros.append(('MODULE_NAME', '"pysqlite2.dbapi2"'))
else:
    define_macros.append(('MODULE_NAME', '\\"pysqlite2.dbapi2\\"'))


def get_amalgamation(dest_path, version=None):
    """Download the SQLite amalgamation if it isn't there, already."""
    if os.path.exists(dest_path):
        print("SQLite amalgamation sources already exist in {}".format(os.path.abspath(dest_path)))
        print("Using existing sources, regardless of version")
        return

    if version is None:
        raise ValueError('The amalgamation parameter was specified, but no sqlite_version parameter was not specified '
                         'and no SQLite amalgamation sources exist')

    try:
        major, minor, release = version.split('.')
    except ValueError:
        raise ValueError('The sqlite_version specified, {}, does not conform to the X.Y.Z version format'
                         .format(version))

    os.makedirs(dest_path)
    print("Downloading SQLite amalgamation sources for version {}.{}.{}".format(major, minor, release))
    amalgamation_filename = "sqlite-amalgamation-{:0<2}{:0<2}{:0<3}.zip".format(major, minor, release)
    amalgamation_url = "http://sqlite.org/2014/{}".format(amalgamation_filename)
    print("Using URL - {}".format(amalgamation_url))
    urllib.urlretrieve(amalgamation_url, amalgamation_filename)

    zf = zipfile.ZipFile(amalgamation_filename)
    files = ["sqlite3.c", "sqlite3.h"]
    directory = zf.namelist()[0]
    for fn in files:
        print "Extracting", fn
        outf = open(os.path.join(dest_path, fn), "wb")
        outf.write(zf.read(directory + fn))
        outf.close()
    zf.close()
    os.unlink(amalgamation_filename)


class DocBuilder(Command):
    description = "Builds the documentation"
    user_options = []

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import os, shutil
        try:
            shutil.rmtree("build/doc")
        except OSError:
            pass
        os.makedirs("build/doc")
        rc = os.system("sphinx-build doc/sphinx build/doc")
        if rc != 0:
            print "Is sphinx installed? If not, try 'sudo easy_install sphinx'."


class MyBuildExt(build_ext):
    amalgamation = False
    sqlite_version = None

    def build_extension(self, ext):
        if self.amalgamation:
            amalgamation_path = os.path.join(self.build_temp, 'sqlite_amalgamation')
            get_amalgamation(amalgamation_path, self.sqlite_version)
            ext.define_macros.append(("SQLITE_ENABLE_FTS3", "1"))   # build with fulltext search enabled
            ext.define_macros.append(("SQLITE_ENABLE_RTREE", "1"))   # build with fulltext search enabled
            ext.sources.append(os.path.join(amalgamation_path, "sqlite3.c"))
            ext.include_dirs.append(amalgamation_path)

        build_ext.build_extension(self, ext)

    def __setattr__(self, k, v):
        # Make sure we don't link against the SQLite library, no matter what setup.cfg says
        if self.amalgamation and k == "libraries":
            v = None
        self.__dict__[k] = v


def get_setup_args():
    PYSQLITE_VERSION = None

    version_re = re.compile('#define PYSQLITE_VERSION "(.*)"')
    f = open(os.path.join("src", "module.h"))
    for line in f:
        match = version_re.match(line)
        if match:
            PYSQLITE_VERSION = match.groups()[0]
            PYSQLITE_MINOR_VERSION = ".".join(PYSQLITE_VERSION.split('.')[:2])
            break
    f.close()

    if not PYSQLITE_VERSION:
        print "Fatal error: PYSQLITE_VERSION could not be detected!"
        sys.exit(1)

    data_files = [("pysqlite2-doc",
                        glob.glob("doc/*.html")
                      + glob.glob("doc/*.txt")
                      + glob.glob("doc/*.css")),
                   ("pysqlite2-doc/code",
                        glob.glob("doc/code/*.py"))]

    py_modules = ["sqlite"]
    setup_args = dict(
        name = "pysqlite",
        version = PYSQLITE_VERSION,
        description = "DB-API 2.0 interface for SQLite 3.x",
        long_description=long_description,
        author = "Gerhard Haering",
        author_email = "gh@ghaering.de",
        license = "zlib/libpng license",
        platforms = "ALL",
        url = "http://pysqlite.googlecode.com/",
        download_url = "http://code.google.com/p/pysqlite/downloads/list",

        # Description of the modules and packages in the distribution
        package_dir = {"pysqlite2": "lib"},
        packages = ["pysqlite2", "pysqlite2.test"] +
                   (["pysqlite2.test.py25"], [])[sys.version_info < (2, 5)],
        scripts = [],
        data_files = data_files,

        ext_modules = [Extension( name="pysqlite2._sqlite",
                                  sources=sources,
                                  include_dirs=include_dirs,
                                  library_dirs=library_dirs,
                                  runtime_library_dirs=runtime_library_dirs,
                                  libraries=libraries,
                                  extra_objects=extra_objects,
                                  define_macros=define_macros
                                  )],
        classifiers = [
        "Development Status :: 5 - Production/Stable",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: zlib/libpng License",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Programming Language :: C",
        "Programming Language :: Python",
        "Topic :: Database :: Database Engines/Servers",
        "Topic :: Software Development :: Libraries :: Python Modules"],
        cmdclass = {"build_docs": DocBuilder}
    )

    setup_args["cmdclass"].update({"build_docs": DocBuilder,
                                   "build_ext": MyBuildExt,
                                   "cross_bdist_wininst": cross_bdist_wininst.bdist_wininst})
    return setup_args


def main():
    setup(**get_setup_args())


if __name__ == "__main__":
    main()
