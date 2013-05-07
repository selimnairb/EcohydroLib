#!/usr/bin/env python
"""@package DumpClimateStationInfo

@brief Dump point climate station information from EcohydroLib metadata to standard output

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
  

Pre conditions:
--------------
1. ClimatePointStation entries have been written to the climate point section of metadata associated with the project directory
   

Post conditions:
----------------
None

Usage:
@code
DumpClimateStationInfo.py -p /path/to/project_dir > file.csv
@endcode
"""
import sys
import os
import argparse

from ecohydrolib.context import Context
from ecohydrolib.metadata import GenericMetadata

parser = argparse.ArgumentParser(description='Dump point climate station information from EcohydroLib metadata to standard output')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                    help='The directory from which metadata should be read')
parser.add_argument('-s', '--separator', dest='separator', required=False, default=',', help='Field separator for output')
args = parser.parse_args()

context = Context(args.projectDir, None) 

s = args.separator

sys.stderr.write("Getting stations from metadata... ")
stations = GenericMetadata.readClimatePointStations(context)
sys.stderr.write("done\n")

for station in stations:
    output = station.id.upper() + s + str(station.latitude) + s + str(station.longitude) + s + str(station.elevation) + s + station.name + os.linesep
    sys.stdout.write(output)
