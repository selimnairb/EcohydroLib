"""@package ecohydroworkflowlib.metadata
    
@brief Classes for writing and reading metadata for Ecohydrology workflows

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
import os
import time
import errno
import ConfigParser
from datetime import datetime


class ClimatePointStation:
    
    FMT_DATE = '%Y-%m-%d %H:%M:%S'
    VAR_PRECIP = 'prcp'
    VAR_SNOW = 'snow'
    VAR_TMIN = 'tmin'
    VAR_TMAX = 'tmax'
    VAR_RH = 'rh'
    VAR_PAR = 'par'
    VAR_WIND2M = 'wspd2m'
    
    def __init__(self):
        self.type = None
        self.id = None
        self.longitude = None
        self.latitude = None
        self.elevation = None
        self.startDate = None
        self.endDate = None
        self.variables = []
        self.data = None
        self.variablesData = {}
        
    def writeToMetadata(self, projectDir):
        """ Write ClimatePointStation data to climate point section of metadata for
            a given project directory
        
            @param projectDir Path of the project whose metadata store is to be written to
        """
        fqId = self.type + GenericMetadata.KEY_SEP + self.id

        climatePoints = GenericMetadata.readClimatePointEntries(projectDir)
        try:
            stations = climatePoints['stations'].split(GenericMetadata.VALUE_DELIM)
        except KeyError:
            stations = []
        # Add station to list of stations if need be
        if fqId not in stations:
            fqId = fqId.lower()
            stations.append(fqId)
            stationsStr = GenericMetadata.VALUE_DELIM.join(stations)
            GenericMetadata.writeClimatePointEntry(projectDir, "stations", stationsStr)
        # Write attributes for station
        keyProto = "station" + GenericMetadata.KEY_SEP + fqId + GenericMetadata.KEY_SEP 
        longitude = keyProto + "longitude"
        GenericMetadata.writeClimatePointEntry(projectDir, longitude, self.longitude)
        latitude = keyProto + "latitude"
        GenericMetadata.writeClimatePointEntry(projectDir, latitude, self.latitude)
        elevation = keyProto + "elevation"
        GenericMetadata.writeClimatePointEntry(projectDir, elevation, self.elevation)
        startDate = keyProto + "startdate"
        GenericMetadata.writeClimatePointEntry(projectDir, startDate, self.startDate.strftime(ClimatePointStation.FMT_DATE))
        endDate = keyProto + "enddate"
        GenericMetadata.writeClimatePointEntry(projectDir, endDate, self.endDate.strftime(ClimatePointStation.FMT_DATE))
        variablesKey = keyProto + "variables"
        variablesValue = GenericMetadata.VALUE_DELIM.join(self.variables)
        GenericMetadata.writeClimatePointEntry(projectDir, variablesKey, variablesValue)
        if self.data != None:
            data = keyProto + "data"
            GenericMetadata.writeClimatePointEntry(projectDir, data, self.data)
        else:
            # Try to write data entries for each variable separately
            vars = self.variablesData.keys()
            for var in vars:
                varKey = keyProto + var + GenericMetadata.KEY_SEP + "data"
                GenericMetadata.writeClimatePointEntry(projectDir, varKey, self.variablesData[var])
    
    
    @classmethod
    def readFromMetadata(cls, projectDir, fqId):
        """ Read ClimatePointStation data from climate point section of metadata for
            a given project directory
        
            @param projectDir String representing the path of the project whose metadata store is to be read from
            @param fqId String representing the fully qualified station ID: <type>_<id>
            
            @return A new ClimatePointStation instance with data populated from metadata
            
            @raise KeyError if required field is not in metadata
        """
        newInstance = ClimatePointStation()
        (newInstance.type, newInstance.id) = fqId.split(GenericMetadata.KEY_SEP)
        
        climate = GenericMetadata.readClimatePointEntries(projectDir)
        keyProto = "station" + GenericMetadata.KEY_SEP + fqId + GenericMetadata.KEY_SEP
        longitude = keyProto + "longitude"
        newInstance.longitude = float(climate[longitude])
        latitude = keyProto + "latitude"
        newInstance.latitude = float(climate[latitude])
        elevation = keyProto + "elevation"
        newInstance.elevation = float(climate[elevation])
        startDate = keyProto + "startdate"
        newInstance.startDate = datetime.strptime(climate[startDate], ClimatePointStation.FMT_DATE)
        endDate = keyProto + "enddate"
        newInstance.endDate = datetime.strptime(climate[endDate], ClimatePointStation.FMT_DATE)
        variablesKey = keyProto + "variables"
        newInstance.variables = climate[variablesKey].split(GenericMetadata.VALUE_DELIM)
        try:
            data = keyProto + "data"
            newInstance.data = climate[data]
        except KeyError:
            pass
        try:
            for var in newInstance.variables:
                varKey = keyProto + var + GenericMetadata.KEY_SEP + "data"
                newInstance.variablesData[var] = climate[varKey]
        except KeyError:
            pass
        
        return newInstance


class GenericMetadata:
    """ Handles metadata persistance.
    
        @note All keys are stored in lower case.
        @note This object is stateless, all methods are static, writes to metadata store
        are written immediately.
        
        @todo Implement lock file semantics as decorators
    """

    VALUE_DELIM = ','
    KEY_SEP = '_'
    METADATA_FILENAME = 'metadata.txt'
    METADATA_LOCKFILE = 'metadata.txt.lock'
    MANIFEST_SECTION = 'MANIFEST'
    PROVENANCE_SECTION = 'PROVENANCE'
    STUDY_AREA_SECTION = 'STUDY_AREA'
    CLIMATE_POINT_SECTION = 'CLIMATE_POINT'
    CLIMATE_GRID_SECTION = 'CLIMATE_GRID'
    

    @staticmethod
    def _writeEntryToSection(projectDir, section, key, value):
        """ Write an entry in the given section to the metadata store for a given project. 
        
            @note Will overwrite a the value for a key that already exists
            
            @param projectDir Path of the project whose metadata store is to be written to
            @param section The section the key is to be written to
            @param key The key to be written to the given section of the project metadata
            @param value The value to be written for key stored in the given section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        lockFilepath = os.path.join(projectDir, GenericMetadata.METADATA_LOCKFILE)
        metadataFilepath = os.path.join(projectDir, GenericMetadata.METADATA_FILENAME)
        if os.path.exists(metadataFilepath):
            if not os.access(metadataFilepath, os.W_OK):
                raise IOError(errno.EACCES, "Unable to write to metadata store for project %s" % \
                              (projectDir,))
        else:
            if not os.access(projectDir, os.W_OK):
                raise IOError(errno.EACCES, "Unable to write to metadata store for project %s" % \
                              (projectDir,))
            # Create metadata file as it does not exist
            metadataFD = open(metadataFilepath, 'w')
            metadataFD.close()
        
        # Wait for lockfile to be relinquished
        while os.path.exists(lockFilepath):
            time.sleep(5)
        # Write lock file
        open(lockFilepath, 'w').close()
        
        # Read metadata store
        config = ConfigParser.RawConfigParser()
        config.read(metadataFilepath)
        # Write new entry
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, key, value)
        # Write metadata store
        config.write(open(metadataFilepath, 'w'))
        
        # Remove lock file
        os.unlink(lockFilepath)
    
    
    @staticmethod
    def writeManifestEntry(projectDir, key, value):
        """ Write a manifest entry to the metadata store for a given project.
            
            @note Will overwrite a the value for a key that already exists
        
            @param projectDir Path of the project whose metadata store is to be written to
            @param key The key to be written to the manifest section of the project metadata
            @param value The value to be written for key stored in the manifest section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata._writeEntryToSection(projectDir, GenericMetadata.MANIFEST_SECTION, key, value)
     
        
    @staticmethod 
    def writeStudyAreaEntry(projectDir, key, value):
        """ Write a study area entry to the metadata store for a given project.
            
            @note Will overwrite a the value for a key that already exists
        
            @param projectDir Path of the project whose metadata store is to be written to
            @param key The key to be written to the study area section of the project metadata
            @param value The value to be written for key stored in the study area section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata._writeEntryToSection(projectDir, GenericMetadata.STUDY_AREA_SECTION, key, value)
    
    
    @staticmethod 
    def writeClimatePointEntry(projectDir, key, value):
        """ Write a point climate entry to the metadata store for a given project.
            
            @note Will overwrite a the value for a key that already exists
        
            @param projectDir Path of the project whose metadata store is to be written to
            @param key The key to be written to the point climate section of the project metadata
            @param value The value to be written for key stored in the point climate section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata._writeEntryToSection(projectDir, GenericMetadata.CLIMATE_POINT_SECTION, key, value)
    
    
    @staticmethod 
    def writeClimateGridEntry(projectDir, key, value):
        """ Write a grid climate entry to the metadata store for a given project.
            
            @note Will overwrite a the value for a key that already exists
        
            @param projectDir Path of the project whose metadata store is to be written to
            @param key The key to be written to the grid climate  section of the project metadata
            @param value The value to be written for key stored in the grid climate  section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata._writeEntryToSection(projectDir, GenericMetadata.CLIMATE_GRID_SECTION, key, value)
    
    
    @staticmethod
    def _readEntriesForSection(projectDir, section):
        """ Read all entries for the given section from the metadata store for a given project
        
            @param projectDir Absolute path of the project whose metadata are to be read
            @param section The section the key is to be written to
            
            @return A dictionary of key/value pairs from the given section of the project metadata
        """
        sectionDict = dict()
        metadataFilepath = os.path.join(projectDir, GenericMetadata.METADATA_FILENAME)
        if os.path.exists(metadataFilepath):
            if not os.access(metadataFilepath, os.R_OK):
                raise IOError(errno.EACCES, "Unable to read metadata store for project %s" % \
                              (projectDir,))
            # Read metadata store
            config = ConfigParser.RawConfigParser()
            config.read(metadataFilepath)
            if config.has_section(section):
                items = config.items(section)
                for item in items:
                    sectionDict[item[0]] = item[1]
        
        return sectionDict
    
    
    @staticmethod
    def readManifestEntries(projectDir):
        """ Read all manifest entries from the metadata store for a given project
        
            @param projectDir Absolute path of the project whose metadata are to be read
            
            @return A dictionary of key/value pairs from the manifest section of the project metadata
        """
        return GenericMetadata._readEntriesForSection(projectDir, GenericMetadata.MANIFEST_SECTION)
    
    
    @staticmethod
    def readStudyAreaEntries(projectDir):
        """ Read all study area entries from the metadata store for a given project
        
            @param projectDir Absolute path of the project whose metadata are to be read
            
            @return A dictionary of key/value pairs from the study area section of the project metadata
        """
        return GenericMetadata._readEntriesForSection(projectDir, GenericMetadata.STUDY_AREA_SECTION)
    
    
    @staticmethod
    def readClimatePointEntries(projectDir):
        """ Read all point climate entries from the metadata store for a given project
        
            @param projectDir Absolute path of the project whose metadata are to be read
            
            @return A dictionary of key/value pairs from the point climate section of the project metadata
        """
        return GenericMetadata._readEntriesForSection(projectDir, GenericMetadata.CLIMATE_POINT_SECTION)
    
    
    @staticmethod
    def readClimatePointStations(projectDir):
        """ Read all climate point stations from metadata and store in ClimatePointStation 
            instances.
            
            @param projectDir Absolute path of the project whose metadata are to be read
            
            @return A list of ClimatePointStation objects
        """
        stationObjects = []
        climatePoints = GenericMetadata.readClimatePointEntries(projectDir)
        stations = [climatePoints['stations']]
        for station in stations:
            stationObjects.append(ClimatePointStation.readFromMetadata(projectDir, station))
        return stationObjects
    
    
    @staticmethod
    def readClimateGridEntries(projectDir):
        """ Read all grid climate entries from the metadata store for a given project
        
            @param projectDir Absolute path of the project whose metadata are to be read
            
            @return A dictionary of key/value pairs from the grid climate  section of the project metadata
        """
        return GenericMetadata._readEntriesForSection(projectDir, GenericMetadata.CLIMATE_GRID_SECTION)

