"""@package ecohydrolib.command.dem
    
@brief EcohydroLib commands related to acquiring Digital Elevation Model (DEM)
data.

This software is provided free of charge under the New BSD License. Please see
the following license information:

Copyright (c) 2015, University of North Carolina at Chapel Hill
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
"""
import os
import sys
import traceback

from ecohydrolib.command.base import Command
from ecohydrolib.command.exceptions import MetadataException
from ecohydrolib.command.exceptions import RunException

from ecohydrolib.metadata import GenericMetadata
from ecohydrolib.metadata import AssetProvenance

from ecohydrolib.spatialdata.utils import isValidSrs
from ecohydrolib.spatialdata.utils import bboxFromString
from ecohydrolib.spatialdata.utils import calculateBoundingBoxCenter
from ecohydrolib.spatialdata.utils import getUTMZoneFromCoordinates
from ecohydrolib.spatialdata.utils import getEPSGStringForUTMZone
from ecohydrolib.spatialdata.utils import getDimensionsForRaster
from ecohydrolib.spatialdata.utils import getSpatialReferenceForRaster

import ecohydrolib.usgsdem


class USGSWCSDEM(Command):
    
    SUPPORTED_COVERAGES = ecohydrolib.usgsdem.COVERAGES.keys()
    DEFAULT_COVERAGE = ecohydrolib.usgsdem.DEFAULT_COVERAGE
    
    DEFAULT_RASTER_RESAMPLE_METHOD = ecohydrolib.usgsdem.DEFAULT_RASTER_RESAMPLE_METHOD
    RASTER_RESAMPLE_METHOD = ecohydrolib.usgsdem.RASTER_RESAMPLE_METHOD
    
    def __init__(self, projectDir, configFile=None, outfp=sys.stdout):
            """ Construct a USGSWCSDEM command.
            Arguments:
            projectDir -- string    The path to the project directory
            configFile -- string    The path to an EcohydroLib configuration file
            outfp -- file-like object    Where output should be written to
            
            """
            super(USGSWCSDEM, self).__init__(projectDir, configFile, outfp)
        
    def checkMetadata(self):
        """ Check to make sure the project directory has the necessary metadata to run this command.
        """
        super(USGSWCSDEM, self).checkMetadata()
        
        # Check for necessary information in metadata 
        if not 'bbox_wgs84' in self.studyArea:
            raise MetadataException("Metadata in project directory %s does not contain a bounding box" % (self.context.projectDir,)) 
    
    def run(self, *args, **kwargs):
        """ Run the command: Acquire USGS DEM data.
        
        Arguments:
        demType -- string    Source dataset from which DEM tile should be extracted.
        outfile -- string    The name of the DEM file to be written.  File extension ".tif" will be added.
        demResolution list<float>[2]    Two floating point numbers representing the desired X and Y output resolution of soil property raster maps; unit: meters.
        srs -- string    Target spatial reference system of output, in EPSG:num format.
        verbose -- boolean    Produce verbose output. Default: False.
        overwrite -- boolean    Overwrite existing output.  Default: False.
        """
        coverage = kwargs.get('coverage', self.DEFAULT_COVERAGE)
        outfile = kwargs.get('outfile', None)
        demResolution = kwargs.get('demResolution', None)
        srs = kwargs.get('srs', None)
        verbose = kwargs.get('verbose', False)
        overwrite = kwargs.get('overwrite', False)
        
        self.checkMetadata()
        
        bbox = bboxFromString(self.studyArea['bbox_wgs84'])
 
        if not outfile:
            outfile = 'DEM'
        demFilename = "%s.tif" % (outfile)    
        
        demResolutionX = demResolutionY = None
        if demResolution:
            demResolutionX = demResolution[0]
            demResolutionY = demResolution[1]
        
        if srs:
            if not isValidSrs(srs):
                msg = "ERROR: '%s' is not a valid spatial reference.  Spatial reference must be of the form 'EPSG:XXXX', e.g. 'EPSG:32617'.  For more information, see: http://www.spatialreference.org/" % (srs,)
                raise RunException(msg)
        else:
            # Default for UTM
            (centerLon, centerLat) = calculateBoundingBoxCenter(bbox)
            (utmZone, isNorth) = getUTMZoneFromCoordinates(centerLon, centerLat)
            srs = getEPSGStringForUTMZone(utmZone, isNorth)
        
        try: 
            (dataFetched, urlFetched) = ecohydrolib.usgsdem.getDEMForBoundingBox(self.context.config, 
                                           self.context.projectDir,
                                           demFilename,
                                           bbox,
                                           srs,
                                           coverage=coverage,
                                           resx=demResolutionX,
                                           resy=demResolutionY,
                                           scale=0.01,
                                           overwrite=overwrite,
                                           verbose=verbose,
                                           outfp=self.outfp)
        except Exception as e:
            traceback.print_exc(file=self.outfp)
            raise RunException(e)
        
        if not dataFetched:
            raise RunException("Failed to download DEM data from URL {0}".format(urlFetched))
        
        # Write metadata entries
        cmdline = GenericMetadata.getCommandLine()
        
        # Write metadata
        demFilepath = os.path.join(self.context.projectDir, demFilename)  
        demSrs = getSpatialReferenceForRaster(demFilepath)
        GenericMetadata.writeStudyAreaEntry(self.context, 'dem_res_x', demSrs[0])
        GenericMetadata.writeStudyAreaEntry(self.context, 'dem_res_y', demSrs[1])
        GenericMetadata.writeStudyAreaEntry(self.context, 'dem_srs', srs)
        
        # Get rows and columns for DEM  
        (columns, rows) = getDimensionsForRaster(demFilepath)
        GenericMetadata.writeStudyAreaEntry(self.context, 'dem_columns', columns)
        GenericMetadata.writeStudyAreaEntry(self.context, 'dem_rows', rows)
        
        # Write provenance
        asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
        asset.name = 'dem'
        asset.dcIdentifier = demFilename
        asset.dcSource = urlFetched
        asset.dcTitle = "Digital Elevation Model ({0})".format(coverage)
        asset.dcPublisher = 'U.S. Geological Survey'
        asset.dcDescription = cmdline
        asset.processingNotes = "Elevation values rescaled from centimeters to meters. "   
        asset.processingNotes += "Spatial grid resampled to {srs} with X resolution {xres} and Y resolution {yres}."
        asset.processingNotes = asset.processingNotes.format(srs=srs,
                                                             xres=demSrs[0],
                                                             yres=demSrs[1])
        asset.writeToMetadata(self.context)
            
        # Write processing history
        GenericMetadata.appendProcessingHistoryItem(self.context, cmdline)