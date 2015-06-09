"""@package ecohydrolib.command.hydroshare
    
@brief EcohydroLib commands related to HydroShare (http://www.hydroshare.org/)
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
import sys

from ecohydrolib.command.base import Command
from ecohydrolib.command.exceptions import MetadataException
from ecohydrolib.command.exceptions import RunException

from ecohydrolib.metadata import GenericMetadata

from ecohydrolib.hydroshare import create_hydroshare_resource

class HydroShareCreateResource(Command):
    
    def __init__(self, projectDir, configFile=None, outfp=sys.stdout):
        """ Construct a HydroShareCreateResource command.
        Arguments:
        projectDir -- string    The path to the project directory
        configFile -- string    The path to an EcohydroLib configuration file
        outfp -- file-like object    Where output should be written to
        
        """
        super(HydroShareCreateResource, self).__init__(projectDir, configFile, outfp)
        
    def checkMetadata(self, *args, **kwargs):
        """ Check to make sure the project directory has the necessary metadata to run this command.
        """
        super(HydroShareCreateResource, self).checkMetadata(args, kwargs)
        
        overwrite = kwargs.get('overwrite', False)
        
        self.hydroshare = GenericMetadata.readHydroShareEntries(self.context)
        if not overwrite and 'resource_id' in self.hydroshare:
            raise MetadataException("HydroShare resource ID is already defined, but overwrite was not specified")
    
    def run(self, *args, **kwargs):
        """ Run the command: Acquire USGS DEM data.
        
        Arguments:
        auth hs_restclient.HydroShareAuth object
        title string representing the title of the resource
        hydroshare_host string representing DNS name of the HydroShare 
            server in which to create the resource
        hydroshare_port int representing the TCP port of the HydroShare 
            server
        use_https True if HTTPS should be used.  Default: False
        resource_type string representing the HydroShare resource type
            that should be used to create the resource
        abstract string representing the abstract of the resource
        keywords list of strings representing the keywords to assign
            to the resource
        create_callback user-defined callable that takes as input a 
            file size in bytes, and generates a callable to provide feedback 
            to the user about the progress of the upload of resource_file.  
            For more information, see:
            http://toolbelt.readthedocs.org/en/latest/uploading-data.html#monitoring-your-streaming-multipart-upload 
        verbose -- boolean    Produce verbose output. Default: False.
        overwrite -- boolean    Overwrite existing output.  Default: False.
        """
        auth = kwargs.get('auth', None)
        if auth is None:
            raise RunException("No HydroShare authentication mechanism was defined.")
        title = kwargs.get('title', None)
        if title is None: 
            raise RunException("Title for new HydroShare resource was not specified.")
        hydroshare_host = kwargs.get('hydroshare_host', None)
        hydroshare_port = kwargs.get('hydroshare_port', None)
        use_https = kwargs.get('use_https', False)
        resource_type = kwargs.get('resource_type', 'GenericResource')
        abstract = kwargs.get('abstract', None)
        keywords = kwargs.get('keywords', None)
        create_callback = kwargs.get('create_callback', None)
        
        verbose = kwargs.get('verbose', False)
        overwrite = kwargs.get('overwrite', False)
        
        self.checkMetadata(overwrite=overwrite)
        
        resource_id = create_hydroshare_resource(self.context, auth, title, 
                                                 hydroshare_host=hydroshare_host, 
                                                 hydroshare_port=hydroshare_port, use_https=use_https, 
                                                 resource_type=resource_type, abstract=abstract, 
                                                 keywords=keywords, create_callback=create_callback,
                                                 verbose=verbose)
        
        # Write metadata entries
        cmdline = GenericMetadata.getCommandLine()
        
        # Write metadata
        GenericMetadata.writeHydroShareEntry(self.context, 'resource_id', resource_id)
        
        # Write processing history
        GenericMetadata.appendProcessingHistoryItem(self.context, cmdline)
