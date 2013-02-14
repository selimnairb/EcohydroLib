"""!

@brief Extract a tile of NLCD 2006 data for bounding box from a locally stored copy of the entire NLCD 2006 dataset
dataset. 

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
   'GDAL/OGR', 'PATH_OF_GDAL_TRANSLATE'
   'NLCD', 'PATH_OF_NLCD2006'

2. The following metadata entry(ies) must be present in the study area section of the metadata associated with the project directory:
   bbox_wgs84
   dem_res_x
   dem_res_y
   dem_srs

Post conditions
---------------
1. Will write the following entry(ies) to the manifest section of metadata associated with the project directory:
   landcover [the name of the landcover raster]  

Usage:
@code
python ./GetNLCDForBoundingbox.py -i macosx2.cfg -p /path/to/project_dir -f NLCD
@endcode

@todo Buffer bounding box to ensure full coverage with valid NLCD data
"""
import os
import sys
import errno
import argparse
import ConfigParser

import ecohydroworkflowlib.metadata as metadata
from ecohydroworkflowlib.spatialdata.utils import extractTileFromRaster
from ecohydroworkflowlib.spatialdata.utils import resampleRaster
from ecohydroworkflowlib.spatialdata.utils import deleteGeoTiff

# Handle command line options
parser = argparse.ArgumentParser(description='Get NLCD data (in GeoTIFF format) for a bounding box from a local copy of the entire NLCD 2006 dataset.')
parser.add_argument('-i', '--configfile', dest='configfile', required=True,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=False,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('-f', '--outfile', dest='outfile', required=True,
                    help='The name of the DEM file to be written.  File extension ".tif" will be added.')
args = parser.parse_args()

if not os.access(args.configfile, os.R_OK):
    raise IOError(errno.EACCES, "Unable to read configuration file %s" %
                  args.configfile)
config = ConfigParser.RawConfigParser()
config.read(args.configfile)

if not config.has_option('GDAL/OGR', 'PATH_OF_GDAL_TRANSLATE'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_GDAL_TRANSLATE'))

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

nlcdRaster = config.get('NLCD', 'PATH_OF_NLCD2006')
if not os.access(nlcdRaster, os.R_OK):
    raise IOError(errno.EACCES, "Not allowed to read NLCD raster %s" % (nlcdRaster,))
nlcdRaster = os.path.abspath(nlcdRaster)

# Get study area parameters
studyArea = metadata.readStudyAreaEntries(projectDir)
bbox = studyArea['bbox_wgs84'].split()
bbox = dict({'minX': float(bbox[0]), 'minY': float(bbox[1]), 'maxX': float(bbox[2]), 'maxY': float(bbox[3]), 'srs': 'EPSG:4326'})
outputrasterresolutionX = studyArea['dem_res_x']
outputrasterresolutionY = studyArea['dem_res_y']
srs = studyArea['dem_srs']

# Get tile from NLCD raster
tmpTileFilename = "%s-TEMP.tif" % (args.outfile)
extractTileFromRaster(config, projectDir, nlcdRaster, tmpTileFilename, bbox)

tmpTileFilepath = os.path.join(projectDir, tmpTileFilename)
# Resample DEM to target srs and resolution
tileFilename = "%s.tif" % (args.outfile)
resampleRaster(config, projectDir, tmpTileFilepath, tileFilename, \
            s_srs=None, t_srs=srs, \
            trX=outputrasterresolutionX, trY=outputrasterresolutionY, \
            resampleMethod='near')
metadata.writeManifestEntry(projectDir, "landcover", tileFilename)

# Clean-up
deleteGeoTiff(tmpTileFilepath)