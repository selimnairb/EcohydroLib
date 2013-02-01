"""!

@brief Query NHDPlus2 database for shapefile of the drainage area of the given streamflow gage.
@brief Resulting shapefile will use WGS84 (EPSG:4326) for its spatial reference. 

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
   'GDAL/OGR', 'PATH_OF_OGR2OGR'
   'NHDPLUS2', 'PATH_OF_NHDPLUS2_DB'
   'NHDPLUS2', 'PATH_OF_NHDPLUS2_CATCHMENT'

2. The following metadata entry(ies) must be present in the study area section of the metadata associated with the project directory:
   nhd_gage_reachcode
   nhd_gage_measure_pct 

Post conditions
---------------
1. Will write the following entry(ies) to the manifest section of metadata associated with the project directory:
   study_area_shapefile [the name of the catchment shapefile] 

Usage:
@code
PYTHONPATH=${PYTHONPATH}:../:../../NHDPlus2Lib:../../SpatialDataLib python2.7 ./GetCatchmentShapefileForStreamflowGage.py -i macosx2.cfg -p ../../../scratchspace/scratch3 -f catchment
@endcode
"""
import os
import sys
import errno
import argparse
import ConfigParser

import ecohydrologyworkflowlib.metadata as metadata
from nhdplus2lib.networkanalysis import getCatchmentShapefileForGage

# Handle command line options
parser = argparse.ArgumentParser(description='Get shapefile for the drainage area of an NHDPlus2 streamflow gage')
parser.add_argument('-i', '--configfile', dest='configfile', required=True,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=False,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('-f', '--outfile', dest='outfile', required=True,
                    help='The name of the catchment shapefile to be written.  File extension ".shp" will be added.  If a file of this name exists, program will silently exit.')
args = parser.parse_args()

if not os.access(args.configfile, os.R_OK):
    raise IOError(errno.EACCES, "Unable to read configuration file %s" %
                  args.configfile)

config = ConfigParser.RawConfigParser()
config.read(args.configfile)

if not config.has_option('GDAL/OGR', 'PATH_OF_OGR2OGR'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_OGR2OGR'))
if not config.has_option('NHDPLUS2', 'PATH_OF_NHDPLUS2_DB'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'NHDPLUS2', 'PATH_OF_NHDPLUS2_DB'))
if not config.has_option('NHDPLUS2', 'PATH_OF_NHDPLUS2_CATCHMENT'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'NHDPLUS2', 'PATH_OF_NHDPLUS2_CATCHMENT'))  

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

# Get study area parameters
studyArea = metadata.readStudyAreaEntries(projectDir)
reachcode = studyArea['nhd_gage_reachcode']
measure = studyArea['nhd_gage_measure_pct']

shapeFilename = "%s.shp" % (args.outfile)
shapeFilepath = os.path.join(projectDir, shapeFilename)
if not os.path.exists(shapeFilepath):
    getCatchmentShapefileForGage(config, projectDir, shapeFilename, reachcode, measure)
    metadata.writeManifestEntry(projectDir, "study_area_shapefile", shapeFilename)
