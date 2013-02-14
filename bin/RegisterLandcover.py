"""!

@brief Register landcover raster into metadata store for a project directory,
copying the raster into the project directory in the process. 

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
   'GDAL/OGR', 'PATH_OF_GDAL_WARP'

2. The following metadata entry(ies) must be present in the study area section of the metadata associated with the project directory:
   bbox_wgs84
   dem_res_x
   dem_res_y
   dem_columns
   dem_rows
   dem_srs

Post conditions
---------------
1. Will write the following entry(ies) to the manifest section of metadata associated with the project directory:
   landcover [the name of the landcover raster]  

Usage:
@code
python ./RegisterLandcover.py -i macosx2.cfg -p /path/to/project_dir -l /landcoverfile/to/register -f landcover
@endcode
"""
import os
import sys
import errno
import argparse
import ConfigParser

import ecohydroworkflowlib.metadata as metadata
from ecohydroworkflowlib.spatialdata.utils import copyRasterToGeoTIFF
from ecohydroworkflowlib.spatialdata.utils import resampleRaster
from ecohydroworkflowlib.spatialdata.utils import getDimensionsForRaster
from ecohydroworkflowlib.spatialdata.utils import getSpatialReferenceForRaster
from ecohydroworkflowlib.spatialdata.utils import getBoundingBoxForRaster
from ecohydroworkflowlib.spatialdata.utils import writeBboxPolygonToShapefile

# Handle command line options
parser = argparse.ArgumentParser(description='Get DEM raster (in GeoTIFF format) for a bounding box from GeoBrain WCS4DEM')
parser.add_argument('-i', '--configfile', dest='configfile', required=True,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=False,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('-l', '--landcoverfile', dest='landcoverfile', required=True,
                    help='The name of the DEM file to be registered.')
parser.add_argument('-f', '--outfile', dest='outfile', required=True,
                    help='The name of the DEM file to be written to the project directory.  File extension ".tif" will be added.')
args = parser.parse_args()

if not os.access(args.configfile, os.R_OK):
    raise IOError(errno.EACCES, "Unable to read configuration file %s" %
                  args.configfile)
config = ConfigParser.RawConfigParser()
config.read(args.configfile)

if not config.has_option('GDAL/OGR', 'PATH_OF_GDAL_WARP'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_GDAL_WARP'))
    
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

if not os.access(args.landcoverfile, os.R_OK):
    raise IOError(errno.EACCES, "Not allowed to read input landcover raster %s" %
                  args.landcoverfile)

# Get study area parameters
studyArea = metadata.readStudyAreaEntries(projectDir)
bbox = studyArea['bbox_wgs84'].split()
bbox = dict({'minX': float(bbox[0]), 'minY': float(bbox[1]), 'maxX': float(bbox[2]), 'maxY': float(bbox[3]), 'srs': 'EPSG:4326'})
demResolutionX = studyArea['dem_res_x']
demResolutionY = studyArea['dem_res_y']
demColumns = studyArea['dem_columns']
demRows = studyArea['dem_rows']
srs = studyArea['dem_srs']

landcoverFilename = "%s%stif" % (args.outfile, os.extsep)
# Overwrite DEM if already present
landcoverFilepath = os.path.join(projectDir, landcoverFilename)
if os.path.exists(landcoverFilepath):
    os.unlink(landcoverFilepath)

# Ensure input landcover has the same projection and resolution as DEM
lcMetadata = getSpatialReferenceForRaster(args.landcoverfile)
lcSrs = lcMetadata[5]
lcX = lcMetadata[0]
lcY = lcMetadata[1]
if (lcSrs != srs) or (lcX != demResolutionX) or (lcY != demResolutionY):
    # Reproject raster, copying into project directory in the process
    # TODO: rework resample raster to interpret inRasterFilename as an abs. path
    resampleRaster(config, projectDir, args.landcoverfile, landcoverFilepath, \
                   s_srs=lcSrs, t_srs=srs, \
                   trX=demResolutionX, trY=demResolutionY, \
                   resampleMethod='near')
else:
    # Copy the raster in to the project directory
    copyRasterToGeoTIFF(config, projectDir, args.landcoverfile, landcoverFilename)

# Make sure extent of resampled raster is the same as the extent of the DEM
newLcMetadata = getDimensionsForRaster(landcoverFilepath)
if (newLcMetadata[0] != demColumns) or (newLcMetadata[1] != demRows):
    # Extents to not match, roll back and bail out
    os.unlink(landcoverFilepath)
    sys.exit("Extent of landcover dataset %s does not match extent of DEM in project directory %s" %
             (landcoverFilename, projectDir))

# Write metadata
metadata.writeManifestEntry(projectDir, "landcover", landcoverFilename)
