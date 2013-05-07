#!/usr/bin/env python
"""@package GetNHDStreamflowGageIdentifiersAndLocation
 
@brief Get NHDPlus2 streamflow gage identifiers (reachcode, measure along reach in percent) for a USGS gage 
@brief Get lat/lon, in WGS84 (EPSG:4326), from gage point layer (Gage_Loc) for gage identified by a source_fea (e.g. USGS Site Number) 

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
   'NHDPLUS2', 'PATH_OF_NHDPLUS2_DB'
   'NHDPLUS2', 'PATH_OF_NHDPLUS2_GAGELOC'

Post conditions
---------------
1. Will write the following entry(ies) to the manifest section of metadata associated with the project directory:
   gage [the name of the streamflow gage shapefile]  
   
2. Will write the following entry(ies) to the study area section of metadata associated with the project directory:
   gage_id_attr [the name of the attribute in the gage shapefile that uniquely identifies a streamflow gage]
   gage_id
   nhd_gage_reachcode
   nhd_gage_measure_pct
   gage_lat_wgs84
   gage_lon_wgs84

Usage:
@code
GetNHDStreamflowGageIdentifiersAndLocation.py -p /path/to/project_dir -g 01589330
@endcode

@note EcohydroLib configuration file must be specified by environmental variable 'ECOHYDROWORKFLOW_CFG',
or -i option must be specified. 
"""
import sys
import argparse

from ecohydrolib.context import Context
from ecohydrolib.metadata import GenericMetadata
from ecohydrolib.metadata import AssetProvenance
from ecohydrolib.nhdplus2.networkanalysis import getNHDReachcodeAndMeasureForGageSourceFea
from ecohydrolib.nhdplus2.networkanalysis import getLocationForStreamGageByGageSourceFea
from ecohydrolib.spatialdata.utils import writeCoordinatePairsToPointShapefile

# Handle command line options
parser = argparse.ArgumentParser(description='Get NHDPlus2 streamflow gage identifiers for a USGS gage.')
parser.add_argument('-i', '--configfile', dest='configfile', required=False,
                    help='The configuration file')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                  help='The directory to which metadata, intermediate, and final files should be saved')
parser.add_argument('-g', '--gageid', dest='gageid', required=True,
                    help='An integer representing the USGS site identifier')
args = parser.parse_args()
cmdline = GenericMetadata.getCommandLine()

configFile = None
if args.configfile:
    configFile = args.configfile

context = Context(args.projectDir, configFile) 

if not context.config.has_option('NHDPLUS2', 'PATH_OF_NHDPLUS2_DB'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'NHDPLUS2', 'PATH_OF_NHDPLUS2_DB'))

if not context.config.has_option('NHDPLUS2', 'PATH_OF_NHDPLUS2_GAGELOC'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'NHDPLUS2', 'PATH_OF_NHDPLUS2_GAGELOC'))

result = getNHDReachcodeAndMeasureForGageSourceFea(context.config, args.gageid)
if result:
    reachcode = result[0]
    measure = result[1]
else:
    reachcode = measure = "Gage not found"

result = getLocationForStreamGageByGageSourceFea(context.config, args.gageid)
if result:
    gage_lat = result[1]
    gage_lon = result[0]
else:
    gage_lat = gage_lon = "Gage not found"

# Write gage coordinates to a shapefile in the project directory
shpFilename = writeCoordinatePairsToPointShapefile(context.projectDir, "gage", 
                                                   "gage_id", [args.gageid], [(gage_lon, gage_lat)])

# Write study area metadata
GenericMetadata.writeStudyAreaEntry(context, 'gage_id_attr', 'gage_id')
GenericMetadata.writeStudyAreaEntry(context, 'gage_id', args.gageid)
GenericMetadata.writeStudyAreaEntry(context, 'nhd_gage_reachcode', reachcode)
GenericMetadata.writeStudyAreaEntry(context, 'nhd_gage_measure_pct', measure)
GenericMetadata.writeStudyAreaEntry(context, 'gage_lat_wgs84', gage_lat)
GenericMetadata.writeStudyAreaEntry(context, 'gage_lon_wgs84', gage_lon)

# Write provenance
asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
asset.name = 'gage'
asset.dcIdentifier = shpFilename
asset.dcSource = 'http://www.horizon-systems.com/NHDPlus/NHDPlusV2_home.php'
asset.dcTitle = 'Streamflow gage'
asset.dcPublisher = 'USGS'
asset.dcDescription = cmdline
asset.writeToMetadata(context)

# Write processing history
GenericMetadata.appendProcessingHistoryItem(context, cmdline)
