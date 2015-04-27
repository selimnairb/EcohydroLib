"""@package ecohydrolib.command.soil
    
@brief EcohydroLib commands related to acquiring soils data

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

from ecohydrolib.spatialdata.utils import bboxFromString
from ecohydrolib.geosciaus import soilwcs
from ecohydrolib.geosciaus.soilwcs import getSoilsRasterDataForBoundingBox

class SoilGridAustralia(Command):
    
    def __init__(self, projectDir, configFile=None, outfp=sys.stdout):
            """ Construct a SoilGridAustralia command.
            Arguments:
            projectDir -- string    The path to the project directory
            configFile -- string    The path to an EcohydroLib configuration file
            outfp -- file-like object    Where output should be written to
            
            """
            super(SoilGridAustralia, self).__init__(projectDir, configFile, outfp)
        
    def checkMetadata(self):
        """ Check to make sure the project directory has the necessary metadata to run this command.
        """
        super(SoilGridAustralia, self).checkMetadata()
        
        # Check for necessary information in metadata 
        if not 'bbox_wgs84' in self.studyArea:
            raise MetadataException("Metadata in project directory %s does not contain a bounding box" % (self.context.projectDir,))
        if not 'dem_srs' in self.studyArea:
            raise MetadataException("Metadata in project directory %s does not contain a spatial reference system" % (self.context.projectDir,))
        if not 'dem_res_x' in self.studyArea:
            raise MetadataException("Metadata in project directory %s does not contain a raster X resolution" % (self.context.projectDir,))
        if not 'dem_res_y' in self.studyArea:
            raise MetadataException("Metadata in project directory %s does not contain a raster Y resolution" % (self.context.projectDir,))    
    
    def run(self, *args, **kwargs):
        """ Run the command: Acquire Australian soils data. 
        
        Arguments:
        verbose -- boolean    Produce verbose output. Default: False.
        overwrite -- boolean    Overwrite existing output.  Default: False.
        """
        verbose = kwargs.get('verbose', False)
        overwrite = kwargs.get('overwrite', False)
        
        self.checkMetadata()
        
        bbox = bboxFromString(self.studyArea['bbox_wgs84'])
        
        try: 
            rasters = getSoilsRasterDataForBoundingBox(self.context.config, 
                                                       self.context.projectDir,
                                                       bbox,
                                                       srs=self.studyArea['dem_srs'],
                                                       resx=self.studyArea['dem_res_x'],
                                                       resy=self.studyArea['dem_res_y'],
                                                       overwrite=overwrite,
                                                       verbose=verbose,
                                                       outfp=self.outfp)
        except Exception as e:
            traceback.print_exc(file=self.outfp)
            raise RunException(e)
        
        # Write metadata entries
        cmdline = GenericMetadata.getCommandLine()
        for attr in rasters.keys():
            (filepath, url) = rasters[attr]
            filename = os.path.basename(filepath)
            asset = AssetProvenance(GenericMetadata.MANIFEST_SECTION)
            asset.name = attr
            asset.dcIdentifier = filename
            asset.dcSource = url
            asset.dcTitle = attr
            asset.dcPublisher = soilwcs.DC_PUBLISHER
            asset.dcDescription = cmdline
            asset.writeToMetadata(self.context)
            
        # Write processing history
        GenericMetadata.appendProcessingHistoryItem(self.context, cmdline)