#!/usr/bin/env python
"""@package GetNLCDForDEMExtent

@brief Extract a tile, the extent derived from the DEM of the project, of NLCD 2006 data 
from a locally stored copy of the entire NLCD 2006 dataset. 

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
   'NLCD', 'PATH_OF_NLCD2006'

2. following metadata entry(ies) must be present in the manifest section of the metadata associated with the project directory:
   dem

3. The following metadata entry(ies) must be present in the study area section of the metadata associated with the project directory:
   bbox_wgs84
   dem_res_x
   dem_res_y
   dem_srs

Post conditions
---------------
1. Will write the following entry(ies) to the manifest section of metadata associated with the project directory:
   landcover [the name of the landcover raster]
   
2. Will write the following entry(ies) to the study area section of metadata associated with the project directory:
   landcover_type=NLCD2006

Usage:
@code
python ./GetNLCDForDEMExtent.py -p /path/to/project_dir
@endcode
"""
import os
import sys
import errno
import argparse

from ecohydrolib.context import Context
from ecohydrolib.metadata import GenericMetadata
from ecohydrolib.metadata import AssetProvenance
from ecohydrolib.spatialdata.utils import bboxFromString
from ecohydrolib.spatialdata.utils import extractTileFromRaster
from ecohydrolib.spatialdata.utils import extractTileFromRasterByRasterExtent
from ecohydrolib.spatialdata.utils import resampleRaster
from ecohydrolib.spatialdata.utils import deleteGeoTiff
from ecohydrolib.spatialdata.utils import getRasterExtentAsBbox
from ecohydrolib.nlcd.daacquery import getNLCDForBoundingBox
from ecohydrolib.nlcd.daacquery import HOST

# Handle command line options
parser = argparse.ArgumentParser(description='Get NLCD data (in GeoTIFF format) for DEM extent from a local copy of the entire NLCD 2006 dataset.')
parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('-s', '--source', dest='source', required=False, choices=['local', 'wcs'], default='wcs',
                    help='Source for NLCD data')
parser.add_argument('-f', '--outfile', dest='outfile', required=False,
                    help='The name of the NLCD file to be written.  File extension ".tif" will be added.')
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
    outfile = "NLCD"
tileFilename = "%s.tif" % (outfile)

# Get name of DEM raster
manifest = GenericMetadata.readManifestEntries(context)
demFilename = manifest['dem']
demFilepath = os.path.join(context.projectDir, demFilename)
demFilepath = os.path.abspath(demFilepath)
bbox = getRasterExtentAsBbox(demFilepath)

# Get study area parameters
studyArea = GenericMetadata.readStudyAreaEntries(context)
outputrasterresolutionX = studyArea['dem_res_x']
outputrasterresolutionY = studyArea['dem_res_y']
srs = studyArea['dem_srs']

if args.source == 'local':

    nlcdURL = 'http://gisdata.usgs.gov/TDDS/DownloadFile.php?TYPE=nlcd2006&FNAME=NLCD2006_landcover_4-20-11_se5.zip'
    nlcdRaster = context.config.get('NLCD', 'PATH_OF_NLCD2006')
    if not os.access(nlcdRaster, os.R_OK):
        raise IOError(errno.EACCES, "Not allowed to read NLCD raster %s" % (nlcdRaster,))
    nlcdRaster = os.path.abspath(nlcdRaster)
    
    sys.stdout.write('Extracting tile from local NLCD data...')
    sys.stdout.flush()
    extractTileFromRasterByRasterExtent(context.config, context.projectDir, demFilepath, nlcdRaster, tileFilename)
    sys.stdout.write('done\n')

else:
    # Download NLCD from WCS
    sys.stdout.write("Downloading NLCD via WCS from %s..." % (HOST,) )
    sys.stdout.flush()
    (returnCode, nlcdURL) = getNLCDForBoundingBox(context.config, context.projectDir, tileFilename, bbox=bbox, 
                                                  resx=outputrasterresolutionX, resy=outputrasterresolutionY, 
                                                  coverage='NLCD2006', srs=srs)
    assert(returnCode)
    sys.stdout.write('done\n')

# Write metadata
GenericMetadata.writeStudyAreaEntry(context, "landcover_type", "NLCD2006")

# Write provenance
asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
asset.name = 'landcover'
asset.dcIdentifier = tileFilename
asset.dcSource = nlcdURL
asset.dcTitle = 'The National Landcover Database 2006'
asset.dcPublisher = 'USGS'
asset.dcDescription = cmdline
asset.writeToMetadata(context)

# Write processing history
GenericMetadata.appendProcessingHistoryItem(context, cmdline)
