#!/usr/bin/env python
"""@package RegisterStudyAreaShapefile

@brief Register shapefile into metadata store for a project directory,
copying the source shapefile into the project directory in the process (if the source
layer is not a shapefile, it will be converted on copy).  Study area will
be projected to WGS84 GCS (EPSG:4326)

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
1. Will write the following entry(ies) to the manifest section of metadata associated with the project directory:
   study_area_shapefile

2. Will write the following entry(ies) to the study area section of metadata associated with the project directory:
   bbox_wgs84

Usage:
@code
python ./RegisterStudyAreaShapefile.py -p /path/to/project_dir -s /shapefile/to/register
@endcode

@note EcohydroLib configuration file must be specified by environmental variable 'ECOHYDROWORKFLOW_CFG',
or -i option must be specified. 
"""
import os
import sys
import errno
import argparse
import textwrap

from ecohydrolib.context import Context
from ecohydrolib.metadata import GenericMetadata
from ecohydrolib.metadata import AssetProvenance
from ecohydrolib.spatialdata.utils import convertFeatureLayerToShapefile

# Handle command line options
parser = argparse.ArgumentParser(description='Register study area shapefile with project')
parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('-s', '--studyAreaLayer', dest='studyAreaLayer', required=True,
                    help='The name of the study area feature layer to be registered.')
parser.add_argument('-b', '--publisher', dest='publisher', required=False,
                    help="The publisher of the DEM dataset, if not supplied 'SELF PUBLISHED' will be used")
parser.add_argument('--overwrite', dest='overwrite', action='store_true', required=False,
                    help='Overwrite existing datasets in the project.  If not specified, program will halt if a dataset already exists.')
args = parser.parse_args()
cmdline = GenericMetadata.getCommandLine()

configFile = None
if args.configfile:
    configFile = args.configfile

context = Context(args.projectDir, configFile) 

if args.publisher:
    publisher = args.publisher
else:
    publisher = 'SELF PUBLISHED'

if not context.config.has_option('GDAL/OGR', 'PATH_OF_OGR2OGR'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_OGR2OGR'))

if not os.access(args.studyAreaLayer, os.R_OK):
    raise IOError(errno.EACCES, "Not allowed to read input study area %s" (args.demfile,))
inStudyAreaPath = os.path.abspath(args.studyAreaLayer)

shpFilename = convertFeatureLayerToShapefile(context.config,  context.projectDir, inStudyAreaPath, "studyarea", overwrite=args.overwrite)

# Write metadata
asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
asset.name = 'study_area_shapefile'
asset.dcIdentifier = shpFilename
asset.dcSource = "file://%s" % (inStudyAreaPath,)
asset.dcTitle = 'Study area shapefile'
asset.dcPublisher = publisher
asset.dcDescription = cmdline
asset.writeToMetadata(context)

# Write processing history
GenericMetadata.appendProcessingHistoryItem(context, cmdline)
