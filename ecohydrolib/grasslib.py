"""@package ecohydrolib.grasslib
    
@brief Class that encapsulated environment setup for using GRASS GIS scripting and low-level APIs

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
import sys
import shutil
import tempfile
import importlib

GRASS_RASTER_RESAMPLE_NEAREST = 'nearest'
GRASS_RASTER_RESAMPLE_BILINEAR = 'bilinear'
GRASS_RASTER_RESAMPLE_BICUBIC = 'bicubic'
GRASS_RASTER_RESAMPLE_METHODS = [GRASS_RASTER_RESAMPLE_NEAREST, 
                                 GRASS_RASTER_RESAMPLE_BILINEAR,
                                 GRASS_RASTER_RESAMPLE_BICUBIC]

DEFAULT_LOCATION = 'default'
DEFAULT_MAPSET = 'PERMANENT'

class GRASSConfig(object):
    def __init__(self, context, dbase, location=None, mapset=None, newLocation=False, overwrite=False):
        """ @brief Constructor for GRASSConfig
        
            @param context ecohydrolib.Context with config containing a GRASS section with GISBASE entry
            @param dbase String representing a GRASS GIS data directory
            @param location String representing a GRASS project location within the data directory; defaults to DEFAULT_LOCATION.
            @param mapset String representing a GRASS mapset within the location; defaults to DEFAULT_MAPSET.
            @param newLocation Boolean, True if this is a new location, False if the location is expected to already exist
            @param overwrite Boolean, if False, constructor will raise an error if newLocation is True and the location already exists
            
            @raise IOError(errno.ENOTDIR) if dbase is not a writable directory
            @raise IOError(errno.EACCESS) if dbase is not writable
            @raise IOError(errno.EEXIST) if location exists and newLocation == True
        """
        self.gisbase = context.config.get('GRASS', 'GISBASE')
        if not location:
            location = DEFAULT_LOCATION
        if not mapset:
            mapset = DEFAULT_MAPSET
        # Make sure dbase exists
        self.dbase = os.path.abspath(dbase)
        if not os.path.exists(self.dbase):
            (grassDbLoc, grassDbName) = os.path.split(self.dbase)
            if not (os.path.isdir(grassDbLoc) and os.access(grassDbLoc, os.W_OK)):
                raise IOError(errno.ENOTDIR, "%s is not a writable directory" % (grassDbLoc,))
            os.makedirs(self.dbase)
        else:
            if not os.access(self.dbase, os.W_OK):
                raise(errno.EACCES, "Not allowed to write to %s" % (self.dbase,))
        # Check if location already exists, if it does, raise an error if newLocation == True
        self.location = location
    
        locationPath = os.path.join(self.dbase, self.location)
        if os.path.exists( locationPath ):
            if newLocation:
                if overwrite:
                    # Delete existing location
                    shutil.rmtree(locationPath)
                else:
                    raise IOError(errno.EEXIST, "Location '%s' already exists in %s" % \
                                  (location, self.dbase))
        self.mapset = mapset

class GRASSLib(object): 
    def __init__(self, grassConfig=None, grassScripting=None, grassAPI=None):
        """ @brief Constructor for GRASSLib
        
            @param grassConfig GRASSConfig instance 
            @param grassScripting Previously imported grass.script (GRASS scripting API), 
            if None, grass.script will be imported
            @param api Previously imported grass.lib.gis (low-level GRASS API); if None
            grass.lib.gis will be imported
        """
        self.grassConfig = grassConfig
        
        if not grassScripting:
            self.script = self._setupGrassScriptingEnvironment()
        else:
            self.script = grassScripting
            
        if not grassAPI:
            self.api = self._setupGrassEnvironment()
        else:
            self.api = grassAPI 

    def _setupGrassScriptingEnvironment(self):
        """ @brief Set up GRASS environment for using GRASS scripting API from 
            Python (e.g. grass.script)
        """
        os.environ['GISBASE'] = self.grassConfig.gisbase
        sys.path.append(os.path.join(self.grassConfig.gisbase, 'etc', 'python'))
        import grass.script.setup as gsetup
        gsetup.init(self.grassConfig.gisbase, \
                    self.grassConfig.dbase, self.grassConfig.location, \
                    self.grassConfig.mapset)

        self.script = importlib.import_module('grass.script')
        return self.script
    
    def _setupGrassEnvironment(self):
        """ @brief Set up GRASS environment for using GRASS low-level API from 
            Python (e.g. grass.lib)
        """
        gisBase = self.grassConfig.gisbase
        sys.path.append(os.path.join(gisBase, 'etc', 'python'))
        os.environ['LD_LIBRARY_PATH'] = os.path.join(gisBase, 'lib')
        os.environ['DYLD_LIBRARY_PATH'] = os.path.join(gisBase, 'lib')
        # Write grassrc
        os.environ['GISRC'] = self._initializeGrassrc()
        os.environ['GIS_LOCK'] = str(os.getpid())
        self.api = importlib.import_module('grass.lib.gis')
        self.api.G_gisinit('')
        return self.api
    
    def _initializeGrassrc(self):
        grassRcFile = tempfile.NamedTemporaryFile(prefix='grassrc-', delete=False)
        grassRcContent = "GISDBASE: %s\nLOCATION_NAME: %s\nMAPSET: %s\n" % \
            (self.grassConfig.dbase, self.grassConfig.location, self.grassConfig.mapset)
        grassRcFile.write(grassRcContent)
        return grassRcFile.name
