#!/usr/bin/env python
"""@package GetSSURGOFeaturesForBoundingbox

@brief Query USDA soil datamart for SSURGO MapunitPolyExtended features and the following 
attributes, computed as a weighted average of the components in each mapunit, for the first 
soil horizon of each mapunit: ksat (chorizon.ksat_r), pctClay (chorizon.claytotal_r), 
pctSilt (chorizon.silttotal_r), pctSand (chorizon.andtotal_r), porosity (chorizon.wsatiated_r), 
'fieldCap' (chorizon.wthirdbar_r), 'avlWatCap' (plant available water capacity; chorizon.awc_r), 
and drnWatCont (drainable water capacity; porosity - fieldCap).  

@note For information on SSURGO attributes see: http://soildatamart.nrcs.usda.gov/SSURGOMetadata.aspx

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

2. The following metadata entry(ies) must be present in the study area section of the metadata associated with the project directory:
   bbox_wgs84
   dem_res_x
   dem_res_y
   dem_srs

Post conditions
---------------
1. Will write the following entry(ies) to the manifest section of metadata associated with the project directory:
   soil_features [the name of the vector file containing the soil features]

Usage:
@code
GetSSURGOFeaturesForBoundingbox.py -p /path/to/project_dir
@endcode

@note EcohydroLib configuration file must be specified by environmental variable 'ECOHYDROWORKFLOW_CFG',
or -i option must be specified.
"""
import os
import sys
import argparse
import textwrap

from ecohydrolib.context import Context
from ecohydrolib.metadata import GenericMetadata
from ecohydrolib.metadata import AssetProvenance

from ecohydrolib.spatialdata.utils import deleteShapefile
from ecohydrolib.spatialdata.utils import bboxFromString
from ecohydrolib.spatialdata.utils import convertGMLToShapefile
from ecohydrolib.ssurgo.featurequery import getMapunitFeaturesForBoundingBox
from ecohydrolib.ssurgo.featurequery import SSURGO_BBOX_TILE_DIVISOR
from ecohydrolib.ssurgo import featurequery
   
# Handle command line options
parser = argparse.ArgumentParser(description='Get SSURGO features for a bounding box')
parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('--tile', dest='tile', required=False, default=False, action='store_true',
                    help='Enable bounding box tiling to download SSURGO data for areas larger than that supported by USDA web service.')
parser.add_argument('--tiledivisor', dest='tiledivisor', required=False, default=SSURGO_BBOX_TILE_DIVISOR, type=float,
                    help='Divisor to use for tiling bounding box.  Larger divisor will result in a greater number of tiles. ' +
                    "Default: {0}".format(SSURGO_BBOX_TILE_DIVISOR))
parser.add_argument('--keeporiginals', dest='keeporiginals', required=False, default=False, action='store_true',
                    help='If True, intermediate SSURGO feature layers will be retained (otherwise they will be deleted)')
parser.add_argument('--nprocesses', dest='nprocesses', required=False, default=None, type=int,
                    help='Number of processes to use for fetching SSURGO tiles in parallel (used only if bounding box needs to be tiled). ' +
                    'If None, number of CPU threads will be used.')
parser.add_argument('--overwrite', dest='overwrite', action='store_true', required=False,
                    help='Overwrite existing SSURGO features shapefile in project directory.  If not specified, program will halt if a dataset already exists.')
args = parser.parse_args()
cmdline = GenericMetadata.getCommandLine()

configFile = None
if args.configfile:
    configFile = args.configfile

context = Context(args.projectDir, configFile) 

if not context.config.has_option('GDAL/OGR', 'PATH_OF_OGR2OGR'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_OGR2OGR'))

# Check if features shapefile already exists
manifest = GenericMetadata.readManifestEntries(context)
if 'soil_features' in manifest:
    if args.overwrite:
        sys.stdout.write('Deleting existing SSURGO features shapefile\n')
        sys.stdout.flush()
        shpFilepath = os.path.join( context.projectDir, manifest['soil_features'] )
        deleteShapefile(shpFilepath)
    else:
        sys.exit( textwrap.fill('SSURGO features already exist in project directory.  Use --overwrite option to overwrite.') )

# Get study area parameters
studyArea = GenericMetadata.readStudyAreaEntries(context)
bbox = bboxFromString(studyArea['bbox_wgs84'])

outputrasterresolutionX = studyArea['dem_res_x']
outputrasterresolutionY = studyArea['dem_res_y']
srs = studyArea['dem_srs']

sys.stdout.write('Downloading SSURGO features for study area from USDA Soil Data mart...\n')
sys.stdout.flush()
shpFilename = getMapunitFeaturesForBoundingBox(context.config, context.projectDir, bbox, 
                                               tileBbox=args.tile, t_srs=srs, tileDivisor=args.tiledivisor,
                                               keepOriginals=args.keeporiginals,
                                               overwrite=args.overwrite,
                                               nprocesses=args.nprocesses)

# Write provenance
asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
asset.name = 'soil_features'
asset.dcIdentifier = shpFilename
asset.dcSource = featurequery.WFS_URL
asset.dcTitle = 'SSURGO soils data'
asset.dcPublisher = 'USDA'
asset.dcDescription = cmdline
asset.writeToMetadata(context)

# Write processing history
GenericMetadata.appendProcessingHistoryItem(context, cmdline)
