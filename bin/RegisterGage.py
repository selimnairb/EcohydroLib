#!/usr/bin/env python
"""@package RegisterGage

@brief Register streamflow gage coordinates from a point shapefile into metadata 
store for a project directory, copying the shapefile into the project directory 
in the process. 

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
1. The following metadata entry(ies) must be present in the study area section of the metadata associated with the project directory:
   bbox_wgs84

Post conditions
---------------
1. Will write the following entry(ies) to the manifest section of metadata associated with the project directory:
   gage [the name of the streamflow gage shapefile]  

2. Will write the following entry(ies) to the study area section of metadata associated with the project directory:
   gage_id_attr [the name of the attribute in the gage shapefile that uniquely identifies a streamflow gage]
   gage_id [the unique ID of the gage in the shapefile]

Usage:
@code
python ./RegisterGage.py -p /path/to/project_dir -g /path/to/gage/shapefile -l layername -a id_attribute -d id_value
@endcode

@note If option -t is not specified, UTM projection (WGS 84 coordinate system) will be inferred
from bounding box center.

@todo Set date in provenance to file modification date
"""
import os
import sys
import errno
import argparse

from ecohydrolib.context import Context
from ecohydrolib.metadata import GenericMetadata
from ecohydrolib.metadata import AssetProvenance
from ecohydrolib.spatialdata.utils import bboxFromString
from ecohydrolib.spatialdata.utils import deleteShapefile
from ecohydrolib.spatialdata.utils import getCoordinatesOfPointsFromShapefile
from ecohydrolib.spatialdata.utils import writeCoordinatePairsToPointShapefile
from ecohydrolib.spatialdata.utils import isCoordinatePairInBoundingBox


# Handle command line options
parser = argparse.ArgumentParser(description='Register streamflow gage shapefile with project')
parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                    help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('-g', '--gageFile', dest='gageFile', required=True,
                    help='The name of the gage shapefile to be registered.')
parser.add_argument('-l', '--layerName', dest='layerName', required=True,
                    help='The name of the layer within the gage shapefile where gage points are located.')
parser.add_argument('-a', '--idAttribute', dest='idAttribute', required=True,
                    help='The name of the attribute field that uniquely identifies gage points.')
parser.add_argument('-d', '--idValue', dest='idValue', required=True,
                    help='The gage ID that uniquely identifies the gage point.')
parser.add_argument('-f', '--outfile', dest='outfile', required=False,
                    help='The name of the gage shapefile to be written to the project directory.  File extension ".shp" will be added.')
parser.add_argument('-b', '--publisher', dest='publisher', required=False,
                    help="The publisher of the stream flow gage location dataset, if not supplied 'SELF PUBLISHED' will be used")
args = parser.parse_args()
cmdline = GenericMetadata.getCommandLine()

configFile = None
if args.configfile:
    configFile = args.configfile

context = Context(args.projectDir, configFile) 

if not os.access(args.gageFile, os.R_OK):
    raise IOError(errno.EACCES, "Not allowed to read input gage shapefile %s" %
                  args.gageFile)
inGagePath = os.path.abspath(args.gageFile)

if args.publisher:
    publisher = args.publisher
else:
    publisher = 'SELF PUBLISHED'

if args.outfile:
    outfile = args.outfile
else:
    outfile = "gage"

# Get study area parameters
studyArea = GenericMetadata.readStudyAreaEntries(context)
bbox = bboxFromString(studyArea['bbox_wgs84'])

outFilename = "%s%sshp" % (outfile, os.extsep)
# Overwrite DEM if already present
outFilepath = os.path.join(context.projectDir, outFilename)
if os.path.exists(outFilepath):
    deleteShapefile(outFilepath)

sys.stdout.write('Importing streamflow gage...')
sys.stdout.flush()

gageIDs = [args.idValue]
coords = getCoordinatesOfPointsFromShapefile(inGagePath, args.layerName,
                                             args.idAttribute, gageIDs)
gage_lon = coords[0][0]
gage_lat = coords[0][1]
coordinates = (gage_lon, gage_lat)

# Ensure gage coordinates are within bounding box
if not isCoordinatePairInBoundingBox(bbox, coordinates):
    sys.exit("Gage coordinates %s, %s do not appear to lie within bounding box %s, %s, %s, %s" %
             ( str(gage_lon), str(gage_lat), str(bbox['minX']), str(bbox['minY']), str(bbox['maxX']), str(bbox['maxY']) ) )

shpFilename = writeCoordinatePairsToPointShapefile(context.projectDir, outfile, "gage_id", gageIDs, [coordinates])

sys.stdout.write('done\n')

# Write metadata
GenericMetadata.writeStudyAreaEntry(context, 'gage_id_attr', 'gage_id')
GenericMetadata.writeStudyAreaEntry(context, 'gage_id', args.idValue)
GenericMetadata.writeStudyAreaEntry(context, 'gage_lat_wgs84', gage_lat)
GenericMetadata.writeStudyAreaEntry(context, 'gage_lon_wgs84', gage_lon)

# Write provenance
asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
asset.name = 'gage'
asset.dcIdentifier = shpFilename
asset.dcSource = "file://%s" % (inGagePath,)
asset.dcTitle = 'Streamflow gage'
asset.dcPublisher = publisher
asset.dcDescription = cmdline
asset.writeToMetadata(context)

# Write processing history
GenericMetadata.appendProcessingHistoryItem(context, cmdline)