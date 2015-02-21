#!/usr/bin/env python
"""@package RegisterDEM

@brief Register digital elevation model (DEM) data into metadata store for a project directory,
copying the DEM file into the project directory in the process.  Will create a study area 
polygon shapefile for the extent of the DEM imported. 

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
   dem [the name of the DEM raster]
   study_area_shapefile [the name of the study area shapefile generated from the DEM raster extent]

2. Will write the following entry(ies) to the study area section of metadata associated with the project directory:
   bbox_wgs84
   dem_res_x [X resolution of the DEM raster in units of the raster's projection]
   dem_res_y [Y resolution of the DEM raster in units of the raster's projection]
   dem_srs [spatial reference system of the DEM, in EPSG:<nnnn> format]
   dem_columns [number of pixels in the X direction]
   dem_rows [number of pixels in the Y direction]

Usage:
@code
python ./RegisterDEM.py -p /path/to/project_dir -d /demfile/to/register
@endcode

@note EcohydroLib configuration file must be specified by environmental variable 'ECOHYDROWORKFLOW_CFG',
or -i option must be specified. 

@todo Add targer SRS, if present, call GDAL warp instead of just copying the file
@todo Set date in provenance to file modification date
"""
import os
import sys
import errno
import argparse
import textwrap

from ecohydrolib.context import Context
from ecohydrolib.metadata import GenericMetadata
from ecohydrolib.metadata import AssetProvenance
from ecohydrolib.spatialdata.utils import isValidSrs
from ecohydrolib.spatialdata.utils import RASTER_RESAMPLE_METHOD
from ecohydrolib.spatialdata.utils import copyRasterToGeoTIFF
from ecohydrolib.spatialdata.utils import resampleRaster
from ecohydrolib.spatialdata.utils import rescaleRaster
from ecohydrolib.spatialdata.utils import getDimensionsForRaster
from ecohydrolib.spatialdata.utils import getSpatialReferenceForRaster
from ecohydrolib.spatialdata.utils import getBoundingBoxForRaster
from ecohydrolib.spatialdata.utils import writeBboxPolygonToShapefile

# Handle command line options
parser = argparse.ArgumentParser(description='Register DEM with project')
parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('-d', '--demfile', dest='demfile', required=True,
                    help='The name of the DEM file to be registered.')
parser.add_argument('-f', '--outfile', dest='outfile', required=False,
                    help='The name of the DEM file to be written to the project directory.  File extension ".tif" will be added.')
parser.add_argument('-b', '--publisher', dest='publisher', required=False,
                    help="The publisher of the DEM dataset, if not supplied 'SELF PUBLISHED' will be used")
parser.add_argument('-c', '--demResolution', dest='demResolution', required=False, nargs=2, type=float,
                    help='Two floating point numbers representing the desired X and Y output resolution of soil property raster maps; unit: meters')
parser.add_argument('-t', '--t_srs', dest='t_srs', required=False, 
                    help='Target spatial reference system of output, in EPSG:num format')
parser.add_argument('-s', '--resampleMethod', dest='resampleMethod', required=False,
                    choices=RASTER_RESAMPLE_METHOD, default='bilinear',
                    help='Method to use to resample DEM (if necessary). Defaults to bilinear.')
parser.add_argument('--scale', dest='scale', required=False, type=float,
                    help='Amount to scale input DEM by')
args = parser.parse_args()
cmdline = GenericMetadata.getCommandLine()

configFile = None
if args.configfile:
    configFile = args.configfile

context = Context(args.projectDir, configFile) 

if not context.config.has_option('GDAL/OGR', 'PATH_OF_GDAL_WARP'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_GDAL_WARP'))

if not os.access(args.demfile, os.R_OK):
    raise IOError(errno.EACCES, "Not allowed to read input DEM %s" (args.demfile,))
inDEMPath = os.path.abspath(args.demfile)
inSpatialMetadata = getSpatialReferenceForRaster(inDEMPath)

resample = False

s_srs = inSpatialMetadata[5]
t_srs = s_srs
if args.t_srs:
    if not isValidSrs(args.t_srs):
        sys.exit(textwrap.fill("ERROR: '%s' is not a valid spatial reference.  Spatial reference must be of the form 'EPSG:XXXX', e.g. 'EPSG:32617'.  For more information, see: http://www.spatialreference.org/" % (args.t_srs,) ) )
    if s_srs != args.t_srs:
        t_srs = args.t_srs
        resample = True

if args.demResolution:
    if args.demResolution[0] != inSpatialMetadata[0] or args.demResolution[1] != inSpatialMetadata[1]:
        resample = True
    demResolutionX = args.demResolution[0]
    demResolutionY = args.demResolution[1]
else:
    demResolutionX = inSpatialMetadata[0]
    demResolutionY = inSpatialMetadata[1]

if args.publisher:
    publisher = args.publisher
else:
    publisher = 'SELF PUBLISHED'

if args.outfile:
    outfile = args.outfile
else:
    outfile = "DEM"

demFilename = "%s%stif" % (outfile, os.extsep)
# Overwrite DEM if already present
demFilepath = os.path.join(context.projectDir, demFilename)
if os.path.exists(demFilepath):
    os.unlink(demFilepath)

outfileTemp = None
demFilenameTemp = None
demFilepathTemp = None
if args.scale:
    outfileTemp = "%s_temp" % (outfile,)
    demFilenameTemp = "%s%stif" % (outfileTemp, os.extsep)
    demFilepathTemp = os.path.join(context.projectDir, demFilenameTemp)

# Copy the raster in to the project directory (reprojecting if need be)
if not resample:
    sys.stdout.write("Importing DEM...")
    sys.stdout.flush()
    if args.scale:
        copyRasterToGeoTIFF(context.config, context.projectDir, inDEMPath, demFilenameTemp)
    else:
        copyRasterToGeoTIFF(context.config, context.projectDir, inDEMPath, demFilename)
else:
    sys.stdout.write("Reprojecting DEM from %s to %s, spatial resolution (%.2f, %.2f) to (%.2f, %.2f)..." % \
                     (s_srs, t_srs, inSpatialMetadata[0], inSpatialMetadata[1],
                      demResolutionX, demResolutionY) )
    sys.stdout.flush()
    if args.scale:
        resampleRaster(context.config, context.projectDir, inDEMPath, demFilenameTemp,
                       s_srs, t_srs, demResolutionX, demResolutionY, args.resampleMethod)
    else:
        resampleRaster(context.config, context.projectDir, inDEMPath, demFilename,
                       s_srs, t_srs, demResolutionX, demResolutionY, args.resampleMethod)

if args.scale:
    rescaleRaster(context.config, context.projectDir, demFilepathTemp, demFilename, args.scale)
    os.unlink(demFilepathTemp)

sys.stdout.write('done\n')
# Get the bounding box for the DEM
bbox = getBoundingBoxForRaster(demFilepath)
# Write a shapefile for the bounding box
shpFilename = writeBboxPolygonToShapefile(bbox, context.projectDir, "studyarea")

# Write metadata
GenericMetadata.writeStudyAreaEntry(context, "bbox_wgs84", "%f %f %f %f" % (bbox['minX'], bbox['minY'], bbox['maxX'], bbox['maxY']))

# Get spatial metadata for DEM
demSpatialMetadata = getSpatialReferenceForRaster(demFilepath)
GenericMetadata.writeStudyAreaEntry(context, "dem_res_x", demSpatialMetadata[0])
GenericMetadata.writeStudyAreaEntry(context, "dem_res_y", demSpatialMetadata[1])
GenericMetadata.writeStudyAreaEntry(context, "dem_srs", demSpatialMetadata[5])

# Get rows and columns for DEM
demFilepath = os.path.join(context.projectDir, demFilename)
(columns, rows) = getDimensionsForRaster(demFilepath)
GenericMetadata.writeStudyAreaEntry(context, "dem_columns", columns)
GenericMetadata.writeStudyAreaEntry(context, "dem_rows", rows)

# Write provenance
inputDEMURL = "file://%s" % (inDEMPath,)
asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
asset.name = 'dem'
asset.dcIdentifier = demFilename
asset.dcSource = inputDEMURL
asset.dcTitle = 'Digital Elevation Model'
asset.dcPublisher = publisher
asset.dcDescription = cmdline
asset.writeToMetadata(context)

asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
asset.name = 'study_area_shapefile'
asset.dcIdentifier = shpFilename
asset.dcSource = inputDEMURL
asset.dcTitle = 'Study area shapefile'
asset.dcPublisher = publisher
asset.dcDescription = cmdline
asset.writeToMetadata(context)

# Write processing history
GenericMetadata.appendProcessingHistoryItem(context, cmdline)
