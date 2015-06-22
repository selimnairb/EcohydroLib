"""@package ecohydrolib.command.landcover
    
@brief EcohydroLib commands related to acquiring landcover data.

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
from ecohydrolib.command.exceptions import CommandException

from ecohydrolib.metadata import GenericMetadata
from ecohydrolib.metadata import AssetProvenance

from ecohydrolib.spatialdata.utils import getRasterExtentAsBbox

import ecohydrolib.usgs.nlcdwcs
from ecohydrolib.usgs.nlcdwcs import getNLCDRasterDataForBoundingBox
from ecohydrolib.usgs.nlcdwcs import LC_TYPE_TO_COVERAGE


KNOWN_LC_TYPES = ['NLCD2006', 'NLCD2011']
DEFAULT_LC_TYPE = 'NLCD2011'

class USGSWCSNLCD(Command):
    
    SUPPORTED_COVERAGES = ecohydrolib.usgs.nlcdwcs.COVERAGES.keys()
    DEFAULT_COVERAGE = ecohydrolib.usgs.nlcdwcs.DEFAULT_COVERAGE
    
    def __init__(self, projectDir, configFile=None, outfp=sys.stdout):
            """ Construct a USGSWCSNLCD command.
            Arguments:
            projectDir -- string    The path to the project directory
            configFile -- string    The path to an EcohydroLib configuration file
            outfp -- file-like object    Where output should be written to
            
            """
            super(USGSWCSNLCD, self).__init__(projectDir, configFile, outfp)
        
    def checkMetadata(self):
        """ Check to make sure the project directory has the necessary metadata to run this command.
        """
        super(USGSWCSNLCD, self).checkMetadata()
        
        # Check for necessary information in metadata 
        self.manifest = GenericMetadata.readManifestEntries(self.context)
        if not 'dem' in self.manifest:
            raise MetadataException("Metadata in project directory %s does not contain a DEM" % (self.context.projectDir,)) 
        if not 'dem_srs' in self.studyArea:
            raise MetadataException("Metadata in project directory %s does not contain a spatial reference system" % (self.context.projectDir,))
        if not 'dem_res_x' in self.studyArea:
            raise MetadataException("Metadata in project directory %s does not contain a raster X resolution" % (self.context.projectDir,))
        if not 'dem_res_y' in self.studyArea:
            raise MetadataException("Metadata in project directory %s does not contain a raster Y resolution" % (self.context.projectDir,))    
    
    def run(self, *args, **kwargs):
        """ Run the command: Acquire NLCD data from USGS WCS web service.
        
        Arguments:
        lctype -- string    Source dataset from which NLCD tile should be extracted.
        outfile -- string    The name of the NLCD file to be written.  File extension ".tif" will be added.
        verbose -- boolean    Produce verbose output. Default: False.
        overwrite -- boolean    Overwrite existing output.  Default: False.
        """
        lctype = kwargs.get('lctype', DEFAULT_LC_TYPE)
        outfile = kwargs.get('outfile', None)
        verbose = kwargs.get('verbose', False)
        overwrite = kwargs.get('overwrite', False)
        
        if lctype not in ecohydrolib.usgs.nlcdwcs.LC_TYPE_TO_COVERAGE:
            msg = "Land cover type {lctype} is not in the list of supported types {types}"
            raise CommandException(msg.format(lctype=lctype, 
                                              types=ecohydrolib.usgs.nlcdwcs.LC_TYPE_TO_COVERAGE))
        
        self.checkMetadata()
        
        demFilename = self.manifest['dem']
        demFilepath = os.path.join(self.context.projectDir, demFilename)
        demFilepath = os.path.abspath(demFilepath)
        bbox = getRasterExtentAsBbox(demFilepath)
 
        if not outfile:
            outfile = 'NLCD'
        try:
            (resp, urlFetched, fname) = getNLCDRasterDataForBoundingBox(self.context.config, 
                                                                        self.context.projectDir,
                                                                        bbox,
                                                                        coverage=LC_TYPE_TO_COVERAGE[lctype],
                                                                        filename=outfile,
                                                                        srs=self.studyArea['dem_srs'],
                                                                        resx=self.studyArea['dem_res_x'],
                                                                        resy=self.studyArea['dem_res_y'],
                                                                        overwrite=overwrite,
                                                                        verbose=verbose,
                                                                        outfp=self.outfp)
            
        except Exception as e:
            traceback.print_exc(file=self.outfp)
            raise RunException(e)
        
        if not resp:
            raise RunException("Failed to download NLCD data from URL {0}".format(urlFetched))
        
        # Write metadata entries
        cmdline = GenericMetadata.getCommandLine()
        GenericMetadata.writeStudyAreaEntry(self.context, "landcover_type", lctype)
        
        # Write provenance
        asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
        asset.name = 'landcover'
        asset.dcIdentifier = fname
        asset.dcSource = urlFetched
        asset.dcTitle = "The National Landcover Database: {0}".format(lctype)
        asset.dcPublisher = 'USGS'
        asset.dcDescription = cmdline
        asset.writeToMetadata(self.context)
        
        # Write processing history
        GenericMetadata.appendProcessingHistoryItem(self.context, cmdline)