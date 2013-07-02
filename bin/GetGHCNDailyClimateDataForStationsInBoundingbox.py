#!/usr/bin/env python
"""@package GetGHCNDailyClimateDataForStationsInBoundingbox

@brief Query NCDC archive for climate data for all stations in the Global 
Historical Climatology Network
(http://www1.ncdc.noaa.gov/pub/data/ghcn/daily/readme.txt) that fall within a
bounding box. Will find all stations within the study area bounding box.  Requires that 
the  GHCN station database be setup using GHCNDSetup.py. Database must be 
stored in a location specified by a configuration file containing the section
'GHCND', and value 'PATH_OF_STATION_DB'.

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
1. Configuration file must define the following sections and values:
   'GHCND', 'PATH_OF_STATION_DB'

2. The following metadata entry(ies) must be present in the study area section of the metadata associated with the project directory:
   bbox_wgs84

Post conditions
---------------
1. Will write ClimatePointStation entries to the climate point section of metadata associated with the project directory:
   
2. Will save climate data files to outdir

Usage:
@code
GetGHCNDailyClimateDataForStationsInBoundingbox.py -p /path/to/project_dir
@endcode

@note EcohydroLib configuration file must be specified by environmental variable 'ECOHYDROWORKFLOW_CFG',
or -i option must be specified. 

@todo parse data files to determine start date, start time, and variables
"""
import os
import sys
import argparse
from datetime import datetime

from ecohydrolib.context import Context
from ecohydrolib.metadata import GenericMetadata
from ecohydrolib.metadata import ClimatePointStation
from ecohydrolib.spatialdata.utils import bboxFromString
#from ecohydrolib.spatialdata.utils import calculateBoundingBoxCenter
from ecohydrolib.climatedata.ghcndquery import findStationsWithinBoundingBox
from ecohydrolib.climatedata.ghcndquery import getClimateDataForStation

# Handle command line options
parser = argparse.ArgumentParser(description='Query NCDC archive for climate data for all Global Historical Climatology Network stations in the study area bounding box.')
parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('-d', '--outdir', dest='outdir', required=False,
                    help='The name of the subdirectory within the project directory to write the climate data to.')
args = parser.parse_args()
cmdline = GenericMetadata.getCommandLine()

configFile = None
if args.configfile:
    configFile = args.configfile

context = Context(args.projectDir, configFile) 

if not context.config.has_option('GHCND', 'PATH_OF_STATION_DB'):
    sys.exit("Config file %s does not define option %s in section %s" % \
          (configFile, 'PATH_OF_STATION_DB', 'GHCND'))

if args.outdir:
    outDir = args.outdir
else:
    outDir = 'climate'
outDirPath = os.path.join(context.projectDir, outDir)
if not os.path.exists(outDirPath):
    os.mkdir(outDirPath)

# Get study area parameters
studyArea = GenericMetadata.readStudyAreaEntries(context)
bbox = bboxFromString(studyArea['bbox_wgs84'])

# Find all GHCN stations within bounding box
stations = findStationsWithinBoundingBox(context.config, bbox)
print "Found %d stations in bounding box, downloading data..." % (len(stations))
# Get data for each station
for station in stations:
    outFile = os.path.join(outDir, station[0])
    returnCode = getClimateDataForStation(context.config, context.projectDir, outFile, station[0])
    assert(returnCode)
    
    # Write metadata
    newStation = ClimatePointStation()
    newStation.type = "GHCN"
    newStation.id = station[0]
    newStation.longitude = station[1]
    newStation.latitude = station[2]
    newStation.elevation = station[3]
    newStation.name = station[4]
    newStation.data = outFile
    #newStation.startDate = datetime.strptime("200001", "%Y%m")
    #newStation.endDate = datetime.strptime("200101", "%Y%m")
    #newStation.variables = [ClimatePointStation.VAR_TMIN, \
    #                    ClimatePointStation.VAR_TMAX]
    newStation.writeToMetadata(context)
    
# Write processing history
GenericMetadata.appendProcessingHistoryItem(context, cmdline)
