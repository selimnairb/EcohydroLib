#!/usr/bin/env python
"""@package RegisterRaster

@brief Register raster into metadata store for a project directory,
copying the raster into the project directory in the process.  Raster type must
be one of GenericMetadata.RASTER_TYPES.

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
   'GDAL/OGR', 'PATH_OF_GDAL_TRANSLATE'
   'GDAL/OGR', 'PATH_OF_GDAL_WARP'

2. The following metadata entry(ies) must be present in the study area section of the metadata associated with the project directory:
   bbox_wgs84
   dem_res_x
   dem_res_y
   dem_columns
   dem_rows
   dem_srs

3. The following metadata entry(ies) must be present in the manifest section of the metadata associated with the project directory:
   dem

Post conditions
---------------
1. Will write the following entry(ies) to the manifest section of metadata associated with the project directory:
   landcover [for GenericMetadata.RASTER_TYPE_LC; the name of the landcover raster] 
   roof_connectivity [for GenericMetadata.RASTER_TYPE_ROOF; the name of the roof raster]
   
2. Will write the following entry(ies) to the study area section of metadata associated with the project directory:
   landcover_type=custom [for GenericMetadata.RASTER_TYPE_LC]

Usage:
@code
RegisterRaster.py -p /path/to/project_dir -t RASTER_TYPE -r /raster/to/register
@endcode

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
from ecohydrolib.spatialdata.utils import bboxFromString
from ecohydrolib.spatialdata.utils import RASTER_RESAMPLE_METHOD
from ecohydrolib.spatialdata.utils import copyRasterToGeoTIFF
from ecohydrolib.spatialdata.utils import resampleRaster
from ecohydrolib.spatialdata.utils import getDimensionsForRaster
from ecohydrolib.spatialdata.utils import getSpatialReferenceForRaster
from ecohydrolib.spatialdata.utils import extractTileFromRasterByRasterExtent

# Handle command line options
parser = argparse.ArgumentParser(description='Register raster dataset with project')
parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('-t', '--type', dest='type', required=True, choices=GenericMetadata.RASTER_TYPES,
                    help='The type of raster dataset.')
parser.add_argument('-r', '--rasterfile', dest='rasterfile', required=True,
                    help='The relative/absolute path of the raster to be registered.')
parser.add_argument('-s', '--resampleMethod', dest='resampleMethod', required=False,
                    choices=RASTER_RESAMPLE_METHOD, default='near',
                    help="Method to use to resample raster to DEM extent and spatial reference (if necessary). Defaults to '%s'." % ('near',) )
parser.add_argument('-f', '--outfile', dest='outfile', required=False,
                    help='The name of the raster to be written to the project directory.  File extension ".tif" will be added.')
parser.add_argument('--force', dest='force', required=False, action='store_true',
                    help='Force registry of raster if extent does not match DEM.')
parser.add_argument('--noresample', dest='noresample', required=False, action='store_true',
                    help='Do not resample raster if its resolution differs from DEM. Will still resample if raster is not in the same spatial reference as DEM.')
parser.add_argument('--clip', dest='clip', required=False, action='store_true',
                    help='Clip raster to DEM extent.  Will re-sample raster using method specified by resamplingMethod option')
parser.add_argument('-b', '--publisher', dest='publisher', required=False,
                    help="The publisher of the raster, if not supplied 'SELF PUBLISHED' will be used")
args = parser.parse_args()
cmdline = GenericMetadata.getCommandLine()

configFile = None
if args.configfile:
    configFile = args.configfile

context = Context(args.projectDir, configFile) 

if not context.config.has_option('GDAL/OGR', 'PATH_OF_GDAL_WARP'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_GDAL_WARP'))
    
if not context.config.has_option('GDAL/OGR', 'PATH_OF_GDAL_TRANSLATE'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_GDAL_TRANSLATE'))

if not os.access(args.rasterfile, os.R_OK):
    raise IOError(errno.EACCES, "Not allowed to read input raster %s" %
                  args.rasterfile)
inRasterPath = os.path.abspath(args.rasterfile)

if args.publisher:
    publisher = args.publisher
else:
    publisher = 'SELF PUBLISHED'

if args.outfile:
    outfile = args.outfile
else:
    outfile = args.type

force = False
if args.force:
    force = True

# Get study area parameters
studyArea = GenericMetadata.readStudyAreaEntries(context)
bbox = bboxFromString(studyArea['bbox_wgs84'])
demResolutionX = float(studyArea['dem_res_x'])
demResolutionY = float(studyArea['dem_res_y'])
demColumns = int(studyArea['dem_columns'])
demRows = int(studyArea['dem_rows'])
srs = studyArea['dem_srs']

rasterFilename = "%s%stif" % (outfile, os.extsep)
# Overwrite raster if already present
rasterFilepath = os.path.join(context.projectDir, rasterFilename)
if os.path.exists(rasterFilepath):
    os.unlink(rasterFilepath)

# Determine whether we need to resample
resample = False
rasterMetadata = getSpatialReferenceForRaster(inRasterPath)
rasterSrs = rasterMetadata[5]
rasterX = float(rasterMetadata[0])
rasterY = float(rasterMetadata[1])
if (rasterSrs != srs):
    resample = True
elif (not args.noresample) and ( (rasterX != demResolutionX) or (rasterY != demResolutionY) ):
    resample = True

if args.clip:
    processingNotes = "Clipping %s raster %s to DEM extent" % (args.type, inRasterPath)
    manifest = GenericMetadata.readManifestEntries(context)
    demFilename = manifest['dem']
    demFilepath = os.path.join(context.projectDir, demFilename)
    demFilepath = os.path.abspath(demFilepath)
    extractTileFromRasterByRasterExtent(context.config, context.projectDir, demFilepath, inRasterPath, rasterFilepath, args.resampleMethod)
else:
    if resample:
        # Reproject raster, copying into project directory in the process
        processingNotes = "Resampling %s raster from %s to %s, spatial resolution (%.2f, %.2f) to (%.2f, %.2f)" % \
            (args.type, rasterSrs, srs, rasterX, rasterX,
             demResolutionX, demResolutionY) 
        sys.stdout.write( textwrap.fill("%s..." % (processingNotes,) ) )
        resampleRaster(context.config, context.projectDir, inRasterPath, rasterFilepath, \
                       s_srs=None, t_srs=srs, \
                       trX=demResolutionX, trY=demResolutionY, \
                       resampleMethod=args.resampleMethod)
    else:
        # Copy the raster in to the project directory
        processingNotes = "Importing %s raster from %s without resampling" % (args.type, inRasterPath)
        sys.stdout.write( textwrap.fill("%s..." % (processingNotes,) ) )
        sys.stdout.flush()
        copyRasterToGeoTIFF(context.config, context.projectDir, inRasterPath, rasterFilename)
sys.stdout.write('done\n')

# Make sure extent of resampled raster is the same as the extent of the DEM
newRasterMetadata = getDimensionsForRaster(rasterFilepath)
if (newRasterMetadata[0] != demColumns) or (newRasterMetadata[1] != demRows):
    if args.type == GenericMetadata.RASTER_TYPE_STREAM_BURNED_DEM:
        # Extents to not match, roll back and bail out
        os.unlink(rasterFilepath)
        sys.exit(textwrap.fill("ERROR: Raster type %s must be the same extent as DEM" % 
                 (GenericMetadata.RASTER_TYPE_STREAM_BURNED_DEM,) ) )
    if not force:
        # Extents to not match, roll back and bail out
        os.unlink(rasterFilepath)
        sys.exit(textwrap.fill("ERROR: Extent of raster dataset %s does not match extent of DEM in project directory %s. Use --force to override.") %
                 (rasterFilename, context.projectDir))

# Write metadata
if GenericMetadata.RASTER_TYPE_LC == args.type:
    GenericMetadata.writeStudyAreaEntry(context, "landcover_type", "custom")

# Write provenance
asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
asset.name = args.type
asset.dcIdentifier = rasterFilename
asset.dcSource = "file://%s" % (inRasterPath,)
asset.dcTitle = args.type
asset.dcPublisher = publisher
asset.dcDescription = cmdline
asset.processingNotes = processingNotes
asset.writeToMetadata(context)

# Write processing history
GenericMetadata.appendProcessingHistoryItem(context, cmdline)

