#!/usr/bin/env python
"""@package GetHYDRO1kDEMForBoundingbox

@brief Extract tile for HYDRO1k digital elevation model (DEM) stored locally

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
   'GDAL/OGR', 'PATH_OF_GDAL_WARP'
   'HYDRO1k', 'PATH_OF_HYDRO1K_DEM'

2. The following metadata entry(ies) must be present in the study area section of the metadata associated with the project directory:
   bbox_wgs84

Post conditions
---------------
1. Will write the following entry(ies) to the manifest section of metadata associated with the project directory:
   dem [the name of the DEM raster]  

2. Will write the following entry(ies) to the study area section of metadata associated with the project directory:
   dem_res_x [X resolution of the DEM raster in units of the raster's projection]
   dem_res_y [Y resolution of the DEM raster in units of the raster's projection]
   dem_srs [spatial reference system of the DEM, in EPSG:<nnnn> format]
   dem_columns [number of pixels in the X direction]
   dem_rows [number of pixels in the Y direction]

Usage:
@code
GetHYDRO1kDEMForBoundingbox.py -p /path/to/project_dir -s 3 3
@endcode

@note EcohydroLib configuration file must be specified by environmental variable 'ECOHYDROWORKFLOW_CFG',
or -i option must be specified. 

@note If option -t is not specified, UTM projection (WGS 84 coordinate system) will be inferred
from bounding box center.

@todo Debug case where t_srs is specified as NAD83, with unit degree, and 1000 is used as default DEM resolution
"""
import os
import sys
import argparse

from ecohydrolib.context import Context
from ecohydrolib.metadata import GenericMetadata
from ecohydrolib.metadata import AssetProvenance
from ecohydrolib.hydro1k import demtile
from ecohydrolib.spatialdata.utils import bboxFromString
from ecohydrolib.spatialdata.utils import resampleRaster
from ecohydrolib.spatialdata.utils import getSpatialReferenceForRaster
from ecohydrolib.spatialdata.utils import getDimensionsForRaster
from ecohydrolib.spatialdata.utils import deleteGeoTiff
from ecohydrolib.spatialdata.utils import calculateBoundingBoxCenter
from ecohydrolib.spatialdata.utils import getUTMZoneFromCoordinates
from ecohydrolib.spatialdata.utils import getEPSGStringForUTMZone

# Handle command line options
parser = argparse.ArgumentParser(description='Get DEM raster (in GeoTIFF format) for a bounding box from GeoBrain WCS4DEM')
parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('-f', '--outfile', dest='outfile', required=False,
                    help='The name of the DEM file to be written.  File extension ".tif" will be added.')
parser.add_argument('-s', '--demResolution', dest='demResolution', required=False, nargs=2, type=float,
                    help='Two floating point numbers representing the desired X and Y output resolution of soil property raster maps; unit: meters if SRS is UTM')
parser.add_argument('-t', '--t_srs', dest='t_srs', required=False, 
                    help='Target spatial reference system of output, in EPSG:num format')
args = parser.parse_args()
cmdline = GenericMetadata.getCommandLine()

configFile = None
if args.configfile:
    configFile = args.configfile

context = Context(args.projectDir, configFile) 

if not context.config.has_option('GDAL/OGR', 'PATH_OF_GDAL_WARP'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_GDAL_WARP'))

if args.outfile:
    outfile = args.outfile
else:
    outfile = "DEM"

demFilename = "%s.tif" % (outfile)
# Overwrite DEM if already present
demFilepath = os.path.join(context.projectDir, demFilename)
if os.path.exists(demFilepath):
    deleteGeoTiff(demFilepath)

# Get study area parameters
studyArea = GenericMetadata.readStudyAreaEntries(context)
bbox = bboxFromString(studyArea['bbox_wgs84'])

# Determine target spatial reference
if args.t_srs:
    t_srs = args.t_srs
else:
    # Default for UTM
    (centerLon, centerLat) = calculateBoundingBoxCenter(bbox)
    (utmZone, isNorth) = getUTMZoneFromCoordinates(centerLon, centerLat)
    t_srs = getEPSGStringForUTMZone(utmZone, isNorth)

# Get DEM from HYDRO1k dataset on disk
tmpDEMFilename = "%s-TEMP.tif" % (outfile)
returnCode = demtile.getDEMForBoundingBox(context.config, context.projectDir, tmpDEMFilename, bbox=bbox, srs=t_srs)
assert(returnCode)
tmpDEMFilepath = os.path.join(context.projectDir, tmpDEMFilename)

if args.demResolution:
    demResolutionX = args.demResolution[0]
    demResolutionY = args.demResolution[1]
else:
    demSrs = getSpatialReferenceForRaster(tmpDEMFilepath)
    demResolutionX = demSrs[0]
    demResolutionY = demSrs[1]
    
# Resample DEM to target srs and resolution
resampleRaster(context.config, context.projectDir, tmpDEMFilepath, demFilename, \
               s_srs=demtile.DEFAULT_CRS, t_srs=t_srs, \
               trX=demResolutionX, trY=demResolutionY)

# Write metadata
GenericMetadata.writeStudyAreaEntry(context, "dem_res_x", demResolutionX)
GenericMetadata.writeStudyAreaEntry(context, "dem_res_y", demResolutionY)
GenericMetadata.writeStudyAreaEntry(context, "dem_srs", t_srs)

# Get rows and columns for DEM
(columns, rows) = getDimensionsForRaster(demFilepath)
GenericMetadata.writeStudyAreaEntry(context, "dem_columns", columns)
GenericMetadata.writeStudyAreaEntry(context, "dem_rows", rows)

# Write provenance
asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
asset.name = 'dem'
asset.dcIdentifier = demFilename
asset.dcSource = 'http://eros.usgs.gov/#/Find_Data/Products_and_Data_Available/gtopo30/hydro/namerica'
asset.dcTitle = 'Digital Elevation Model from HYDRO1k'
asset.dcPublisher = 'USGS'
asset.dcDescription = cmdline
asset.writeToMetadata(context)

# Write processing history
GenericMetadata.appendProcessingHistoryItem(context, cmdline)

# Clean-up
deleteGeoTiff(tmpDEMFilepath)