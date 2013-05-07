#!/usr/bin/env python
"""@package GetCatchmentShapefileForHYDRO1kBasins

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
   'GDAL/OGR', 'PATH_OF_OGR2OGR'
   'HYDRO1k', 'PATH_OF_HYDRO1K_BAS'
   'HYDRO1k', 'HYDRO1k_BAS_LAYER_NAME'
   
Post conditions
---------------
1. Will write the following entry(ies) to the manifest section of metadata associated with the project directory:
   study_area_shapefile [the name of the catchment shapefile] 

Usage:
@code
GetCatchmentShapefileForHYDRO1kBasins.py -p /path/to/project_dir -b <basin1> <basin2> ... <basinN>
@endcode

@note EcohydroLib configuration file must be specified by environmental variable 'ECOHYDROWORKFLOW_CFG',
or -i option must be specified. 
"""
import os
import sys
import argparse

from ecohydrolib.context import Context
from ecohydrolib.metadata import GenericMetadata
from ecohydrolib.metadata import AssetProvenance
from ecohydrolib.hydro1k.basins import getCatchmentShapefileForHYDRO1kBasins

# Handle command line options
parser = argparse.ArgumentParser(description='Get shapefile for the drainage area of an NHDPlus2 streamflow gage')
parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('-f', '--outfile', dest='outfile', required=False,
                    help='The name of the catchment shapefile to be written.  File extension ".shp" will be added.  If a file of this name exists, program will silently exit.')
parser.add_argument('-b', '--basins', dest='basins', nargs='+', required=True,
                    help='HYDRO1k basins to extract')
args = parser.parse_args()
cmdline = GenericMetadata.getCommandLine()

configFile = None
if args.configfile:
    configFile = args.configfile

context = Context(args.projectDir, configFile) 

if not context.config.has_option('GDAL/OGR', 'PATH_OF_OGR2OGR'):
    sys.exit("Config file %s does not define option %s in section %s" % \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_OGR2OGR'))
if not context.config.has_option('HYDRO1k', 'PATH_OF_HYDRO1K_BAS'):
    sys.exit("Config file %s does not define option %s in section %s" % \
          (args.configfile, 'HYDRO1k', 'PATH_OF_HYDRO1K_BAS'))
if not context.config.has_option('HYDRO1k', 'HYDRO1k_BAS_LAYER_NAME'):
    sys.exit("Config file %s does not define option %s in section %s" % \
          (args.configfile, 'HYDRO1k', 'HYDRO1k_BAS_LAYER_NAME'))
  
if args.outfile:
    outfile = args.outfile
else:
    outfile = "catchment"

shapeFilename = "%s.shp" % (outfile)
shapeFilepath = os.path.join(context.projectDir, shapeFilename)
if not os.path.exists(shapeFilepath):
    getCatchmentShapefileForHYDRO1kBasins(context.config, context.projectDir, shapeFilename, args.basins)
    
    # Write provenance
    asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
    asset.name = 'study_area_shapefile'
    asset.dcIdentifier = shapeFilename
    asset.dcSource = 'http://eros.usgs.gov/#/Find_Data/Products_and_Data_Available/gtopo30/hydro/namerica'
    asset.dcTitle = 'Study area shapefile derived from HYDRO1k Basins'
    asset.dcPublisher = 'USGS'
    asset.dcDescription = cmdline
    asset.writeToMetadata(context)

    # Write processing history
    GenericMetadata.appendProcessingHistoryItem(context, cmdline)
    