#!/usr/bin/env python
"""@package GenerateSoilPropertyRastersFromSOLIM

@brief Infer soil attributes associated with SSURGO mapunit features using SOLIM

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
   'SOLIM', 'PATH_OF_SOLIM'

2. The following metadata entry(ies) must be present in the manifest section of the metadata associated with the project directory:
   soil_features [the name of the vector file containing the soil features]

3. The following metadata entry(ies) must be present in the study area section of the metadata associated with the project directory:
   dem_res_x
   dem_res_y

Post conditions
---------------
1. Will write the following entry(ies) to the manifest section of metadata associated with the project directory:
   soil_raster_<attr> [the name of the raster file for each soil property raster]

Usage:
@code
GenerateSoilPropertyRastersFromSOLIM.py -p /path/to/project_dir
@endcode

@note EcohydroLib configuration file must be specified by environmental variable 'ECOHYDROWORKFLOW_CFG',
or -i option must be specified.

@todo Recognize when DEM resolution is less than 10m, resample temporary DEM, run SOLIM with resampled DEM
"""
import os
import sys
import argparse

from ecohydrolib.context import Context
from ecohydrolib.metadata import GenericMetadata
from ecohydrolib.metadata import AssetProvenance
from ecohydrolib.ssurgo import rasterize
from ecohydrolib.ssurgo import attributequery
from ecohydrolib.solim.inference import inferSoilPropertiesForSSURGOAndTerrainData     

# Handle command line options
parser = argparse.ArgumentParser(description='Get SSURGO features for a bounding box')
parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                    help='The directory to which metadata, intermediate, and final files should be saved')
args = parser.parse_args()
cmdline = GenericMetadata.getCommandLine()

configFile = None
if args.configfile:
    configFile = args.configfile

context = Context(args.projectDir, configFile) 

if not context.config.has_option('SOLIM', 'PATH_OF_SOLIM'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'SOLIM', 'PATH_OF_SOLIM'))

# Get provenance data for SSURGO
ssurgoProvenance = [i for i in GenericMetadata.readAssetProvenanceObjects(context) if i.name == 'soil_features'][0]
if ssurgoProvenance is None:
    sys.exit("Unable to load SSURGO provenance information from metadata")

# Get manifest entries
manifest = GenericMetadata.readManifestEntries(context)
shpFilename = manifest['soil_features']
shpFilepath = os.path.join(context.projectDir, shpFilename)
demFilename = manifest['dem']
demFilepath = os.path.join(context.projectDir, demFilename)
layerName = os.path.splitext(shpFilename)[0]

# Get study area parameters
studyArea = GenericMetadata.readStudyAreaEntries(context)
outputrasterresolutionX = studyArea['dem_res_x']
outputrasterresolutionY = studyArea['dem_res_y']

# Truncate attributes to 10 characters because shapefiles rely on ancient technology
sys.stdout.write('Generating soil property maps using SOLIM...')
sys.stdout.flush()
attrList = [elem[:10] for elem in attributequery.ATTRIBUTE_LIST_NUMERIC] 
rasterFiles = inferSoilPropertiesForSSURGOAndTerrainData(config=context.config, outputDir=context.projectDir, \
                                                         shpFilepath=shpFilepath, demFilepath=demFilepath, \
                                                         featureAttrList=attrList)
sys.stdout.write('done\n')

# Write metadata entries
for attr in rasterFiles.keys():
    asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
    asset.name = "soil_raster_%s" % (attr,)
    asset.dcIdentifier = rasterFiles[attr]
    asset.dcSource = 'http://solim.geography.wisc.edu'
    asset.dcTitle = attr
    asset.dcPublisher = 'Department of Geography, UW-Madison'
    asset.dcDescription = cmdline
    asset.writeToMetadata(context)

# Write processing history
GenericMetadata.appendProcessingHistoryItem(context, cmdline)