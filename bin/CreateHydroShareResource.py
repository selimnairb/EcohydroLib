#!/usr/bin/env python
"""@package GetUSGSDEMForBoundingbox

@brief Create a new HydroShare resource by uploading the contents of an
EcohydroLib project.

This software is provided free of charge under the New BSD License. Please see
the following license information:

Copyright (c) 2015, University of North Carolina at Chapel Hill
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
"""
import sys
import os
import argparse
import traceback
import getpass

from ecohydrolib.hydroshare import create_console_callback
from ecohydrolib.hydroshare import get_password_authentication

from ecohydrolib.command.exceptions import *
from ecohydrolib.command.hydroshare import HydroShareCreateResource

if __name__ == "__main__":
    # Handle command line options
    parser = argparse.ArgumentParser(description='Create a new HydroShare resource by uploading the contents of an EcohydroLib project.')
    parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                        help='The configuration file.')
    parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                        help='The directory to which metadata, intermediate, and final files should be saved')
    parser.add_argument('--title', dest='title', required=True,
                        help='The title of the HydroShare resource to create.')
    parser.add_argument('--abstract', dest='abstract', 
                        help='The abstract of the new resource.')
    parser.add_argument('--keywords', dest='keywords', nargs='+',
                        help='Key works to associate with the new resource.')
    parser.add_argument('--overwrite', dest='overwrite', action='store_true', required=False,
                        help='Overwrite existing data in project directory.  If not specified, program will halt if a dataset already exists.')
    args = parser.parse_args()
    
    configFile = None
    if args.configfile:
        configFile = args.configfile
        
    command = HydroShareCreateResource(args.projectDir, configFile)
    
    exitCode = os.EX_OK
    try: 
        
        sys.stdout.write('HydroShare username (this will not be stored on disk): ')
        username = sys.stdin.readline().strip()
        password = getpass.getpass('HydroShare password (this will not be stored on disk): ')
        auth = get_password_authentication(username, password)
        
        command.run(auth=auth,
                    title=args.title,
                    abstract=args.abstract,
                    keywords=args.keywords,
                    create_callback=create_console_callback,
                    verbose=True, 
                    overwrite=args.overwrite)
    except CommandException as e:
        traceback.print_exc(file=sys.stderr)
        exitCode = os.EX_DATAERR
    
    sys.exit(exitCode)