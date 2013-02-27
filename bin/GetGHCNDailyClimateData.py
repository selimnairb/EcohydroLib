#!/usr/bin/env python
"""@package GetGHCNDailyClimateData

@brief Query NCDC archive for climate data for a single station in the Global 
Historical Climatology Network
(http://www1.ncdc.noaa.gov/pub/data/ghcn/daily/readme.txt). Will find the 
nearest station to the centroid of the study area bounding box.  Requires that 
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
1. Will write the following entry(ies) to the manifest section of metadata associated with the project directory:
   ghcn_climate_data [the name of the GHCN data file]  

2. Will write the following entry(ies) to the study area section of metadata associated with the project directory:
   ghcn_station_id
   ghcn_station_longitude
   ghcn_station_latitude
   ghcn_station_elevation_m
   ghcn_station_distance

Usage:
@code
GetGHCNDailyClimateData.py -p /path/to/project_dir
@endcode

@note EcoHydroWorkflowLib configuration file must be specified by environmental variable 'ECOHYDROWORKFLOW_CFG',
or -i option must be specified. 
"""
import os
import sys
import errno
import argparse
import ConfigParser

import ecohydroworkflowlib.metadata as metadata
from ecohydroworkflowlib.spatialdata.utils import calculateBoundingBoxCenter
from ecohydroworkflowlib.climatedata.ghcndquery import findStationNearestToCoordinates
from ecohydroworkflowlib.climatedata.ghcndquery import getClimateDataForStation

# Handle command line options
parser = argparse.ArgumentParser(description='Query NCDC archive for climate data for a single station in the Global Historical Climatology Network')
parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=False,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('-f', '--outfile', dest='outfile', required=False,
                    help='The name of the file to write the climate data to.')
args = parser.parse_args()

configFile = None
if args.configfile:
    configFile = args.configfile
else:
    try:
        configFile = os.environ['ECOHYDROWORKFLOW_CFG']
    except KeyError:
        sys.exit("Configuration file not specified via environmental variable\n'ECOHYDROWORKFLOW_CFG', and -i option not specified")
if not os.access(configFile, os.R_OK):
    raise IOError(errno.EACCES, "Unable to read configuration file %s" %
                  configFile)
config = ConfigParser.RawConfigParser()
config.read(configFile)

print "Config file: %s" % (configFile,)

if not config.has_option('GHCND', 'PATH_OF_STATION_DB'):
    sys.exit("Config file %s does not define option %s in section %s" % \
          (configFile, 'PATH_OF_STATION_DB', 'GHCND'))

if args.projectDir:
    projectDir = args.projectDir
else:
    projectDir = os.getcwd()
if not os.path.isdir(projectDir):
    raise IOError(errno.ENOTDIR, "Project directory %s is not a directory" % (projectDir,))
if not os.access(projectDir, os.W_OK):
    raise IOError(errno.EACCES, "Not allowed to write to project directory %s" %
                  projectDir)
projectDir = os.path.abspath(projectDir)

if args.outfile:
    outfile = args.outfile
else:
    outfile = "clim.txt"

# Get study area parameters
studyArea = metadata.readStudyAreaEntries(projectDir)
bbox = studyArea['bbox_wgs84'].split()
bbox = dict({'minX': float(bbox[0]), 'minY': float(bbox[1]), 'maxX': float(bbox[2]), 'maxY': float(bbox[3]), 'srs': 'EPSG:4326'})

# Get centroid of bounding box
(longitude, latitude) = calculateBoundingBoxCenter(bbox)
print("Longitude %f, latitude %f" % (longitude, latitude))
# Find nearest GHCN station
nearest = findStationNearestToCoordinates(config, longitude, latitude)
print(nearest)
# Get data for station
returnCode = getClimateDataForStation(config, projectDir, outfile, nearest[0])
assert(returnCode)

# Write metadata
metadata.writeManifestEntry(projectDir, "ghcn_climate_data", outfile)
metadata.writeStudyAreaEntry(projectDir, "ghcn_station_id", nearest[0])
metadata.writeStudyAreaEntry(projectDir, "ghcn_station_longitude", nearest[1])
metadata.writeStudyAreaEntry(projectDir, "ghcn_station_latitude", nearest[2])
metadata.writeStudyAreaEntry(projectDir, "ghcn_station_elevation_m", nearest[3])
metadata.writeStudyAreaEntry(projectDir, "ghcn_station_distance", nearest[4])