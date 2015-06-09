#!/usr/bin/env python
"""@package GetUSGSDEMForBoundingbox

@brief Download 1/3 arcsecond Digital Elevation Model (DEM) data from
National Elevation Dataset and NHDPlus hydro-conditioned coverages
hosted by U.S. Geological Survey Web Coverage Service (WCS) interface.

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

from ecohydrolib.command.exceptions import *
from ecohydrolib.command.dem import USGSWCSDEM

if __name__ == "__main__":
    # Handle command line options
    parser = argparse.ArgumentParser(description='Download NED DEM data via USGS-hosted WCS web')
    parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                        help='The configuration file.')
    parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                        help='The directory to which metadata, intermediate, and final files should be saved')
    parser.add_argument('-s', '--resampleMethod', dest='resampleMethod', required=False,
                        choices=USGSWCSDEM.RASTER_RESAMPLE_METHOD, default=USGSWCSDEM.DEFAULT_RASTER_RESAMPLE_METHOD,
                        help="Method to use to resample raster to DEM extent and spatial reference (if necessary). Defaults to '%s'." % (USGSWCSDEM.DEFAULT_RASTER_RESAMPLE_METHOD,) )
    parser.add_argument('-f', '--outfile', dest='outfile', required=False,
                        help='The name of the DEM file to be written.  File extension ".tif" will be added.')
    parser.add_argument('-c', '--demResolution', dest='demResolution', required=False, nargs=2, type=float,
                        help='Two floating point numbers representing the desired X and Y output resolution of soil property raster maps; unit: meters')
    parser.add_argument('--srs', dest='srs', required=False, 
                        help='Target spatial reference system of output, in EPSG:num format')
    parser.add_argument('--overwrite', dest='overwrite', action='store_true', required=False,
                        help='Overwrite existing data in project directory.  If not specified, program will halt if a dataset already exists.')
    parser.add_argument('-v', '--verbose', dest='verbose', action='store_true',
                        help='Print detailed information about what the program is doing')
    args = parser.parse_args()
    
    configFile = None
    if args.configfile:
        configFile = args.configfile
        
    command = USGSWCSDEM(args.projectDir, configFile)
    
    exitCode = os.EX_OK
    try: 
        command.run(coverage=USGSWCSDEM.DEFAULT_COVERAGE,
                    outfile=args.outfile,
                    demResolution=args.demResolution,
                    srs=args.srs,
                    interpolation=args.resampleMethod,
                    verbose=args.verbose, 
                    overwrite=args.overwrite)
    except CommandException as e:
        traceback.print_exc(file=sys.stderr)
        exitCode = os.EX_DATAERR
    
    sys.exit(exitCode)