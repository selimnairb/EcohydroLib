#!/usr/bin/env python
"""@package RunCmd

@brief Run an arbitrary command operating on data stored in a project directory,
with the command and its arguments captured in the metadata for the project.

This software is provided free of charge under the New BSD License. Please see
the following license information:

Copyright (c) 2013, University of North Carolina at Chapel Hill
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:
    * Redistributions of source code must retain the above copyright
      notice, this list of conditions and the following disclaimer.
    * Redistributions in binary form must reproduce the above copyright
      notice, this list of conditions and the following disclaimer in the
      documentation and/or other materials provided with the distribution.
    * Neither the name of the University of North Carolina at Chapel Hill nor the
      names of its contributors may be used to endorse or promote products
      derived from this software without specific prior written permission.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE UNIVERSITY OF NORTH CAROLINA AT CHAPEL HILL
BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR 
CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE
GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION)
HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT 
LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT
OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.


@author Brian Miles <brian_miles@unc.edu>
  
  
Pre conditions
--------------
None

Post conditions
---------------
1. Will write an entry to the history section of the project metadata

Usage:
@code
RunCmd.py -p /path/to/project_dir COMMAND [ARG1 ... ARGN]
@endcode
"""
import os
import sys
import errno
import argparse
import textwrap
import subprocess

from ecohydrolib.context import Context
from ecohydrolib.metadata import GenericMetadata
import ecohydrolib.util

# Handle command line options
parser = argparse.ArgumentParser(description='Run arbitrary command against data in project, recording the command in history metadata')
parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('command')
parser.add_argument('args', nargs=argparse.REMAINDER)
args = parser.parse_args()

configFile = None
if args.configfile:
    configFile = args.configfile

context = Context(args.projectDir, configFile) 

# Run command
cmd = ecohydrolib.util.getAbsolutePathOfExecutable(args.command)
if cmd == None:
    sys.exit("Enable able to find command '%s'" % (args.command,) )

result = subprocess.call( [cmd] + args.args )
if result != 0:
    sys.exit("Command '%s' failed returning %d" % (args.command, result) )

# Build representation of command with absolute path of all command arguments
cmdline = cmd
for arg in args.args:
    cmdline += ' ' + ecohydrolib.util.getAbsolutePathOfItem(arg)

# Write processing history
GenericMetadata.appendProcessingHistoryItem(context, cmdline)

