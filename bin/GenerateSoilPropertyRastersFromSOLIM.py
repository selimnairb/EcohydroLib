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

@note EcoHydroWorkflowLib configuration file must be specified by environmental variable 'ECOHYDROWORKFLOW_CFG',
or -i option must be specified.

@todo Recognize when DEM resolution is less than 10m, resample temporary DEM, run SOLIM with resampled DEM
"""
import os
import sys
import errno
import argparse
import ConfigParser

import ecohydroworkflowlib.metadata as metadata
import ecohydroworkflowlib.ssurgo.attributequery
from ecohydroworkflowlib.solim.inference import inferSoilPropertiesForSSURGOAndTerrainData     

# Handle command line options
parser = argparse.ArgumentParser(description='Get SSURGO features for a bounding box')
parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=False,
                    help='The directory to which metadata, intermediate, and final files should be saved')
args = parser.parse_args()

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

if not config.has_option('SOLIM', 'PATH_OF_SOLIM'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'SOLIM', 'PATH_OF_SOLIM'))

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

# Get manifest entries
manifest = metadata.readManifestEntries(projectDir)
shpFilename = manifest['soil_features']
shpFilepath = os.path.join(projectDir, shpFilename)
demFilename = manifest['dem']
demFilepath = os.path.join(projectDir, demFilename)
layerName = os.path.splitext(shpFilename)[0]

# Get study area parameters
studyArea = metadata.readStudyAreaEntries(projectDir)
outputrasterresolutionX = studyArea['dem_res_x']
outputrasterresolutionY = studyArea['dem_res_y']

# Truncate attributes to 10 characters because shapefiles rely on ancient technology
attrList = [elem[:10] for elem in ecohydroworkflowlib.ssurgo.attributequery.attributeListNumeric] 
rasterFiles = inferSoilPropertiesForSSURGOAndTerrainData(config=config, outputDir=projectDir, \
                                                         shpFilepath=shpFilepath, demFilepath=demFilepath, \
                                                         featureAttrList=attrList)
# Write metadata entries
for attr in rasterFiles.keys():
    metadata.writeManifestEntry(projectDir, "soil_raster_%s" % (attr,), rasterFiles[attr])

