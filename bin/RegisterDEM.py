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

@note EcoHydroWorkflowLib configuration file must be specified by environmental variable 'ECOHYDROWORKFLOW_CFG',
or -i option must be specified. 

@todo Add targer SRS, if present, call GDAL warp instead of just copying the file
"""
import os
import sys
import errno
import argparse
import ConfigParser

from ecohydroworkflowlib.metadata import GenericMetadata
from ecohydroworkflowlib.metadata import AssetProvenance
from ecohydroworkflowlib.spatialdata.utils import copyRasterToGeoTIFF
from ecohydroworkflowlib.spatialdata.utils import getDimensionsForRaster
from ecohydroworkflowlib.spatialdata.utils import getSpatialReferenceForRaster
from ecohydroworkflowlib.spatialdata.utils import getBoundingBoxForRaster
from ecohydroworkflowlib.spatialdata.utils import writeBboxPolygonToShapefile

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
                    help="The publisher of the landcover dataset, if not supplied 'SELF PUBLISHED' will be used")
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

if not os.access(args.demfile, os.R_OK):
    raise IOError(errno.EACCES, "Not allowed to read input DEM %s" (args.demfile,))
inDEMPath = os.path.abspath(args.demfile)

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
demFilepath = os.path.join(projectDir, demFilename)
if os.path.exists(demFilepath):
    os.unlink(demFilepath)

# Copy the raster in to the project directory
copyRasterToGeoTIFF(config, projectDir, inDEMPath, demFilename)
# Get the bounding box for the DEM
bbox = getBoundingBoxForRaster(demFilepath)
# Write a shapefile for the bounding box
shpFilename = writeBboxPolygonToShapefile(bbox, projectDir, "studyarea")

# Write metadata
GenericMetadata.writeStudyAreaEntry(projectDir, "bbox_wgs84", "%f %f %f %f" % (bbox['minX'], bbox['minY'], bbox['maxX'], bbox['maxY']))

# Get spatial metadata for DEM
demSpatialMetadata = getSpatialReferenceForRaster(demFilepath)
GenericMetadata.writeStudyAreaEntry(projectDir, "dem_res_x", demSpatialMetadata[0])
GenericMetadata.writeStudyAreaEntry(projectDir, "dem_res_y", demSpatialMetadata[1])
GenericMetadata.writeStudyAreaEntry(projectDir, "dem_srs", demSpatialMetadata[5])

# Get rows and columns for DEM
demFilepath = os.path.join(projectDir, demFilename)
(columns, rows) = getDimensionsForRaster(demFilepath)
GenericMetadata.writeStudyAreaEntry(projectDir, "dem_columns", columns)
GenericMetadata.writeStudyAreaEntry(projectDir, "dem_rows", rows)

# Write provenance
inputDEMURL = "file://%s" % (inDEMPath,)
asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
asset.name = 'dem'
asset.dcIdentifier = demFilename
asset.dcSource = inputDEMURL
asset.dcTitle = 'Digital Elevation Model'
asset.dcPublisher = publisher
asset.dcDescription = cmdline
asset.writeToMetadata(projectDir)

asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
asset.name = 'study_area_shapefile'
asset.dcIdentifier = shpFilename
asset.dcSource = inputDEMURL
asset.dcTitle = 'Study area shapefile'
asset.dcPublisher = publisher
asset.dcDescription = cmdline
asset.writeToMetadata(projectDir)

# Write processing history
GenericMetadata.appendProcessingHistoryItem(projectDir, cmdline)
