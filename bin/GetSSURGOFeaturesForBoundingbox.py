"""!

@brief Query USDA soil datamart for SSURGO features and attributes

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
   'GDAL/OGR', 'PATH_OF_GDAL_RASTERIZE'

2. The following metadata entry(ies) must be present in the study area section of the metadata associated with the project directory:
   bbox_wgs84
   dem_res_x
   dem_res_y
   dem_srs

Post conditions
---------------
1. Will write the following entry(ies) to the manifest section of metadata associated with the project directory:
   soil_features [the name of the vector file containing the soil features]
   soil_raster_<attr> [the name of the raster file for each soil property raster]

Usage:
@code
python ./GetSSURGOFeaturesForBoundingbox.py -i macosx2.cfg -p /path/to/project_dir
@encode
"""
import os
import sys
import errno
import argparse
import ConfigParser

import ecohydrologyworkflowlib.metadata as metadata
from spatialdatalib.utils import convertGMLToShapefile
from ssurgolib.featurequery import getMapunitFeaturesForBoundingBox
from ssurgolib.rasterize import rasterizeSSURGOFeatures
import ssurgolib.attributequery     

# Handle command line options
parser = argparse.ArgumentParser(description='Get SSURGO features for a bounding box')
parser.add_argument('-i', '--configfile', dest='configfile', required=True,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=False,
                    help='The directory to which metadata, intermediate, and final files should be saved')
args = parser.parse_args()

if not os.access(args.configfile, os.R_OK):
    raise IOError(errno.EACCES, "Unable to read configuration file %s" %
                  args.configfile)
config = ConfigParser.RawConfigParser()
config.read(args.configfile)

if not config.has_option('GDAL/OGR', 'PATH_OF_OGR2OGR'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_OGR2OGR'))
if not config.has_option('GDAL/OGR', 'PATH_OF_GDAL_RASTERIZE'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_GDAL_RASTERIZE'))

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
bbox = studyArea['bbox_wgs84'].split()
bbox = dict({'minX': float(bbox[0]), 'minY': float(bbox[1]), 'maxX': float(bbox[2]), 'maxY': float(bbox[3]), 'srs': 'EPSG:4326'})
outputrasterresolutionX = studyArea['dem_res_x']
outputrasterresolutionY = studyArea['dem_res_y']
srs = studyArea['dem_srs']

gmlFilename = getMapunitFeaturesForBoundingBox(projectDir, bbox, mapunitExtended=True, tileBbox=False)[0]
    
# Convert from gml to shp and then rasterize
gmlFilepath = os.path.join(projectDir, gmlFilename)
layerName = os.path.splitext(gmlFilename)[0]
shpFilename = convertGMLToShapefile(config, projectDir, gmlFilepath, layerName, srs)
metadata.writeManifestEntry(projectDir, "soil_features", shpFilename)

# Truncate attributes to 10 characters because shapefiles rely on ancient technology
attrList = [elem[:10] for elem in ssurgolib.attributequery.attributeListNumeric] 
rasterFiles = rasterizeSSURGOFeatures(config=config, outputDir=projectDir, featureFilename=shpFilename, featureLayername=layerName, \
                                      featureAttrList=attrList, \
                                      rasterResolutionX=outputrasterresolutionX, rasterResolutionY=outputrasterresolutionY)
# Write metadata entries
for attr in rasterFiles.keys():
    metadata.writeManifestEntry(projectDir, "soil_raster_%s" % (attr,), rasterFiles[attr])

