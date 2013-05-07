#!/usr/bin/env python
"""@package GetBoundingboxFromStudyareaShapefile

@brief Get bounding box for ESRI Shapefile projected in WGS84 (EPSG:4326)

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
1. The following metadata entry(ies) must be present in the manifest section of the metadata associated with the project directory: 
   study_area_shapefile [the name of the of the study area shapefile]

Post conditions:
----------------
1. Will write the following entry(ies) to the study area section of metadata associated with the project directory:
   bbox_wgs84

Usage:
@code
GetBoundingboxFromStudyareaShapefile.py -p /path/to/project_dir
@endcode
"""
import os
import errno
import argparse

from ecohydrolib.context import Context
from ecohydrolib.metadata import GenericMetadata
from ecohydrolib.spatialdata.utils import getBoundingBoxForShapefile

# Handle command line options
parser = argparse.ArgumentParser(description='Get bounding box from study area shapefile')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('-b', '--buffer', dest='buffer', required=False,
                    help='Number of WGS84 degrees by which to buffer the bounding box')
args = parser.parse_args()
cmdline = GenericMetadata.getCommandLine()

context = Context(args.projectDir, None)

buffer = 0.01
if args.buffer:
    buffer = float(args.buffer)

# Get name of study area shapefile
manifest = GenericMetadata.readManifestEntries(context)
shapefileName = manifest['study_area_shapefile']

shapefilePath = os.path.join(context.projectDir, shapefileName)
if not os.access(shapefilePath, os.R_OK):
    raise IOError(errno.EACCES, "Unable to read shapefile %s" %
                  args.shapefile)

# Get bounding box, buffer by about 1 km
bbox = getBoundingBoxForShapefile(shapefilePath, buffer=buffer)
GenericMetadata.writeStudyAreaEntry(context, "bbox_wgs84", "%f %f %f %f" % (bbox['minX'], bbox['minY'], bbox['maxX'], bbox['maxY']))

# Write processing history
GenericMetadata.appendProcessingHistoryItem(context, cmdline)