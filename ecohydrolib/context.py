"""@package ecohydrolib.context
    
@brief Class that encapsulated environment setup for ecohydrolib scripts

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
"""
import os, errno
import ConfigParser

from ecohydrolib.metadata import GenericMetadata

CONFIG_FILE_ENV = 'ECOHYDROLIB_CFG'

class Context(object):
    def __init__(self, projectDir, configFile=None):
        """ Constructor for Context class
        
            @param projectDir Path of the project whose metadata store is to be read from
            @param configFile Path of ecohydrolib configuration file to use.  If none,
            will attempt to read configuration from a file named in the environment
            variable Context.CONFIG_FILE_ENV
            
            @raise IOError if project directory path is not a directory
            @raise IOError if project directory is not writable
            @raise MetadataVersionError if a version already exists in the 
            metadata store and is different than GenericMetadata._ecohydrolibVersion
            @raise EnvironmentError if configuration file name could not be read from the 
            environment
            @raise IOError if configuration file could not be read
        """
        if not os.path.isdir(projectDir):
            raise IOError(errno.ENOTDIR, "Specified project directory %s is not a directory" % \
                          (projectDir,))
        if not os.access(projectDir, os.W_OK):
            raise IOError(errno.EACCES, "Unable to write to project directory %s" % \
                          (projectDir,))
        self.projectDir = os.path.abspath(projectDir)
        
        # Make sure metadata version is compatible with this version of ecohydrolib
        #   will raise MetadataVersionError if there is a version mismatch
        GenericMetadata.checkMetadataVersion(projectDir)
        
        if not configFile:
            try:
                self._configFile = os.environ[CONFIG_FILE_ENV]
            except KeyError:
                raise EnvironmentError("Configuration file not specified via environmental variable %s" %\
                                       CONFIG_FILE_ENV)
        else:
            self._configFile = configFile
        
        if not os.access(self._configFile, os.R_OK):
            raise IOError(errno.EACCES, "Unable to read configuration file %s" %
                          self._configFile)
        self.config = ConfigParser.RawConfigParser()
        self.config.read(self._configFile)