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

@note EcoHydroWorkflowLib configuration file must be specified by environmental variable 'ECOHYDROWORKFLOW_CFG',
or -i option must be specified. 

@note If option -t is not specified, UTM projection (WGS 84 coordinate system) will be inferred
from bounding box center.
"""
import os
import sys
import errno
import argparse
import ConfigParser

from ecohydroworkflowlib.metadata import GenericMetadata
from ecohydroworkflowlib.metadata import AssetProvenance
from ecohydroworkflowlib.hydro1k import demtile
from ecohydroworkflowlib.spatialdata.utils import resampleRaster
from ecohydroworkflowlib.spatialdata.utils import getSpatialReferenceForRaster
from ecohydroworkflowlib.spatialdata.utils import getDimensionsForRaster
from ecohydroworkflowlib.spatialdata.utils import deleteGeoTiff
from ecohydroworkflowlib.spatialdata.utils import calculateBoundingBoxCenter
from ecohydroworkflowlib.spatialdata.utils import getUTMZoneFromCoordinates
from ecohydroworkflowlib.spatialdata.utils import getEPSGStringForUTMZone

# Handle command line options
parser = argparse.ArgumentParser(description='Get DEM raster (in GeoTIFF format) for a bounding box from GeoBrain WCS4DEM')
parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('-f', '--outfile', dest='outfile', required=False,
                    help='The name of the DEM file to be written.  File extension ".tif" will be added.')
parser.add_argument('-s', '--demResolution', dest='demResolution', required=False, nargs=2, type=float,
                    help='Two floating point numbers representing the desired X and Y output resolution of soil property raster maps; unit: meters')
parser.add_argument('-t', '--t_srs', dest='t_srs', required=False, 
                    help='Target spatial reference system of output, in EPSG:num format')
args = parser.parse_args()
cmdline = " ".join(sys.argv[:])

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

if not config.has_option('GDAL/OGR', 'PATH_OF_GDAL_WARP'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_GDAL_WARP'))

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
    outfile = "DEM"

demFilename = "%s.tif" % (outfile)
# Overwrite DEM if already present
demFilepath = os.path.join(projectDir, demFilename)
if os.path.exists(demFilepath):
    deleteGeoTiff(demFilepath)

# Get study area parameters
studyArea = GenericMetadata.readStudyAreaEntries(projectDir)
bbox = studyArea['bbox_wgs84'].split()
bbox = dict({'minX': float(bbox[0]), 'minY': float(bbox[1]), 'maxX': float(bbox[2]), 'maxY': float(bbox[3]), 'srs': 'EPSG:4326'})

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
returnCode = demtile.getDEMForBoundingBox(config, projectDir, tmpDEMFilename, bbox=bbox, srs=t_srs)
assert(returnCode)
tmpDEMFilepath = os.path.join(projectDir, tmpDEMFilename)

if args.demResolution:
    demResolutionX = args.demResolution[0]
    demResolutionY = args.demResolution[1]
else:
    demSrs = getSpatialReferenceForRaster(tmpDEMFilepath)
    demResolutionX = demSrs[0]
    demResolutionY = demSrs[1]
    
# Resample DEM to target srs and resolution
resampleRaster(config, projectDir, tmpDEMFilepath, demFilename, \
               s_srs=demtile.DEFAULT_CRS, t_srs=t_srs, \
               trX=demResolutionX, trY=demResolutionY)

# Write metadata
GenericMetadata.writeStudyAreaEntry(projectDir, "dem_res_x", demResolutionX)
GenericMetadata.writeStudyAreaEntry(projectDir, "dem_res_y", demResolutionY)
GenericMetadata.writeStudyAreaEntry(projectDir, "dem_srs", t_srs)

# Get rows and columns for DEM
(columns, rows) = getDimensionsForRaster(demFilepath)
GenericMetadata.writeStudyAreaEntry(projectDir, "dem_columns", columns)
GenericMetadata.writeStudyAreaEntry(projectDir, "dem_rows", rows)

# Write provenance
#GenericMetadata.writeManifestEntry(projectDir, "dem", demFilename)
asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
asset.name = 'dem'
asset.dcIdentifier = demFilename
asset.dcSource = 'http://eros.usgs.gov/#/Find_Data/Products_and_Data_Available/gtopo30/hydro/namerica'
asset.dcTitle = 'Digital Elevation Model from HYDRO1k'
asset.dcPublisher = 'USGS'
asset.dcDescription = cmdline
asset.writeToMetadata(projectDir)

# Write processing history
GenericMetadata.appendProcessingHistoryItem(projectDir, cmdline)

# Clean-up
deleteGeoTiff(tmpDEMFilepath)