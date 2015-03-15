"""@package ecohydrolib.command.base
    
@brief Base classes for EcohydroLib commands

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
import sys

from ecohydrolib.grasslib import *

from ecohydrolib.command.exceptions import MetadataException
from ecohydrolib.context import Context
from ecohydrolib.metadata import GenericMetadata

class Command(object):
    def __init__(self, projectDir, configFile=None, outfp=sys.stdout):
        """ Construct a EcohydroLib abstract command.  Concrete commands
            must call this super class method in their constructor.
        
        Arguments:
        projectDir -- string    The path to the project directory
        configFile -- string    The path to an EcohydroLib configuration file
        outfp -- file-like object    Where output should be written to
        
        """
        self.context = Context(projectDir, configFile) 
        self.outfp = outfp
    
    def checkMetadata(self, *args, **kwargs):
        """ Check to make sure the project directory has the necessary metadata to run this command.
        
            @note Concrete commands must call this super class method in their own
            implementation of checkMetadata(), and must call their implementation
            near the beginning of their run method.
        
        """
        self.studyArea = GenericMetadata.readStudyAreaEntries(self.context)
        
    def run(self, *args, **kwargs):
        """ Run the command
        
            @note Concrete classes must call checkMetadata() near the beginning
            of their run methods. 
        """
        raise NotImplementedError()
    

class GrassCommand(Command):
    def __init__(self, projectDir, configFile=None, outfp=sys.stdout):
        """ Construct a EcohydroLib abstract command that runs GRASS commands.  
            Concrete GRASS commands must call this super class method in their constructor.
        
        Arguments:
        projectDir -- string    The path to the project directory
        configFile -- string    The path to an EcohydroLib configuration file
        outfp -- file-like object    Where output should be written to
        
        """
        super(GrassCommand, self).__init__(projectDir, configFile, outfp)
        
    def checkMetadata(self, *args, **kwargs):
        """ Check to make sure the project directory has the necessary metadata to run this command.
        
            @note Concrete commands must call this super class method in their own
            implementation of checkMetadata(), and must call their implementation
            near the beginning of their run method.
        
        """
        super(GrassCommand, self).checkMetadata()
        self.grassMetadata = GenericMetadata.readGRASSEntries(self.context)
        
        if not 'grass_dbase' in self.metadata:
            raise MetadataException("Metadata in project directory %s does not contain a GRASS Dbase" % (self.context.projectDir,)) 
        if not 'grass_location' in self.metadata:
            raise MetadataException("Metadata in project directory %s does not contain a GRASS location" % (self.context.projectDir,)) 
        if not 'grass_mapset' in self.metadata:
            raise MetadataException("Metadata in project directory %s does not contain a GRASS mapset" % (self.context.projectDir,))
        
        self.setupGrassEnv()

    def setupGrassEnv(self):
        self.modulePath = self.context.config.get('GRASS', 'MODULE_PATH')
        self.grassDbase = os.path.join(self.context.projectDir, self.metadata['grass_dbase'])
        self.grassConfig = GRASSConfig(self.context, self.grassDbase, self.metadata['grass_location'], self.metadata['grass_mapset'])
        self.grassLib = GRASSLib(grassConfig=self.grassConfig)
        
    def run(self, *args, **kwargs):
        """ Run the command
        
            @note Concrete classes must call checkMetadata() near the beginning
            of their run methods. 
        """
        raise NotImplementedError()
