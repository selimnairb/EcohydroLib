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

@todo Refactor storage of climate station to embedded database
"""
import os
import time
import errno
import ConfigParser
from datetime import datetime


class MetadataEntity:
    """ Abstract class for encoding structured data to be written to a metadata store
    """
    def writeToMetadata(self, projectDir):
        """ Write structured entity to metadata store for a given project directory
        
            @param projectDir Path of the project whose metadata store is to be written to
        """
        pass
    
    @classmethod
    def readFromMetadata(cls, projectDir, fqId):
        """ Read structured entity from metadata store for a given project directory
        
            @param projectDir String representing the path of the project whose metadata store is to be read from
            @param fqId String representing the fully qualified ID of the entity
            
            Implementations should return an instance of themselves containing data read from the metadata store
            
            @raise KeyError if entity is not in metadata
        """
        pass


class ClimatePointStation(MetadataEntity):
    
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
        self.name = None
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
        fqId = self.type + GenericMetadata.COMPOUND_KEY_SEP + self.id
        fqId = fqId.lower()

        climatePoints = GenericMetadata.readClimatePointEntries(projectDir)
        try:
            stations = climatePoints['stations'].split(GenericMetadata.VALUE_DELIM)
        except KeyError:
            stations = []
        # Write station metadata (overwrite if already present)
        keys = []
        values = []
        if fqId not in stations:
            stations.append(fqId)
            stationsStr = GenericMetadata.VALUE_DELIM.join(stations)
            keys.append('stations'); values.append(stationsStr)
        # Write attributes for station
        keyProto = 'station' + GenericMetadata.COMPOUND_KEY_SEP + fqId + GenericMetadata.COMPOUND_KEY_SEP 
        longitude = keyProto + 'longitude'
        keys.append(longitude); values.append(self.longitude)
        latitude = keyProto + 'latitude'
        keys.append(latitude); values.append(self.latitude)
        elevation = keyProto + 'elevation'
        keys.append(elevation); values.append(self.elevation)
        name = keyProto + 'name'
        keys.append(name); values.append(self.name)
        if self.startDate:
            startDate = keyProto + 'startdate'
            keys.append(startDate); values.append(self.startDate.strftime(ClimatePointStation.FMT_DATE))
        if self.endDate:
            endDate = keyProto + 'enddate'
            keys.append(endDate); values.append(self.endDate.strftime(ClimatePointStation.FMT_DATE))
        if self.variables:
            variablesKey = keyProto + 'variables'
            variablesValue = GenericMetadata.VALUE_DELIM.join(self.variables)
            keys.append(variablesKey); values.append(variablesValue)
        if self.data != None:
            data = keyProto + 'data'
            keys.append(data); values.append(self.data)
        elif self.variablesData:
            # Try to write data entries for each variable separately
            vars = self.variablesData.keys()
            for var in vars:
                varKey = keyProto + var + GenericMetadata.COMPOUND_KEY_SEP + 'data'
                keys.append(varKey); values.append(self.variablesData[var])
        GenericMetadata.writeClimatePointEntries(projectDir, keys, values)
    
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
        (newInstance.type, newInstance.id) = fqId.split(GenericMetadata.COMPOUND_KEY_SEP)

        climate = GenericMetadata.readClimatePointEntries(projectDir)
        
        keyProto = 'station' + GenericMetadata.COMPOUND_KEY_SEP + fqId + GenericMetadata.COMPOUND_KEY_SEP
        longitude = keyProto + 'longitude'
        newInstance.longitude = float(climate[longitude])
        latitude = keyProto + 'latitude'
        newInstance.latitude = float(climate[latitude])
        elevation = keyProto + 'elevation'
        newInstance.elevation = float(climate[elevation])
        name = keyProto + 'name'
        newInstance.name = climate[name]      
        startDate = keyProto + 'startdate'
        try:
            newInstance.startDate = datetime.strptime(climate[startDate], ClimatePointStation.FMT_DATE)
        except KeyError:
            pass    
        endDate = keyProto + 'enddate'
        try:
            newInstance.endDate = datetime.strptime(climate[endDate], ClimatePointStation.FMT_DATE)
        except KeyError:
            pass
        variablesKey = keyProto + 'variables'
        try:
            newInstance.variables = climate[variablesKey].split(GenericMetadata.VALUE_DELIM)
        except KeyError:
            pass
        data = keyProto + 'data'
        try:
            newInstance.data = climate[data]
        except KeyError:
            pass
        try:
            for var in newInstance.variables:
                varKey = keyProto + var + GenericMetadata.COMPOUND_KEY_SEP + 'data'
                newInstance.variablesData[var] = climate[varKey]
        except KeyError:
            pass
       
        return newInstance


class AssetProvenance(MetadataEntity):
    
    FMT_DATE = '%Y-%m-%d %H:%M:%S'
    
    def __init__(self, section=None):
        self.section = section
        self.name = None
        self.dcIdentifier = None
        self.dcSource = None
        self.dcTitle = None
        self.dcDate = datetime.now()
        self.dcPublisher = None
        self.dcDescription = None
        
    def writeToMetadata(self, projectDir):
        """ Write AssetProvenance data to provenance section of metadata for
            a given project directory
        
            @param projectDir Path of the project whose metadata store is to be written to
            @exception Exception if section is not a valid GenericMetadata section
        """
        fqId = self.section + GenericMetadata.COMPOUND_KEY_SEP + self.name
        fqId = fqId.lower()
        
        # Write self to the appropriate section
        GenericMetadata.writeEntryToSection(projectDir, self.section, self.name, self.dcIdentifier)
        
        # Write to provenance section
        provenanceEntries = GenericMetadata.readProvenanceEntries(projectDir)
        try:
            entities = provenanceEntries['entities'].split(GenericMetadata.VALUE_DELIM)
        except KeyError:
            entities = []
        # Write entity metadata (overwrite if already present)
        keys = []
        values = []
        if fqId not in entities:
            entities.append(fqId)
            entitiesStr = GenericMetadata.VALUE_DELIM.join(entities)
            keys.append('entities'); values.append(entitiesStr)
        # Write attributes for entity
        keyProto = fqId + GenericMetadata.COMPOUND_KEY_SEP
        dcIdentifier = keyProto + 'dc.identifier'
        keys.append(dcIdentifier); values.append(self.dcIdentifier)
        dcSource = keyProto + 'dc.source'
        keys.append(dcSource); values.append(self.dcSource)
        dcTitle = keyProto + 'dc.title'
        keys.append(dcTitle); values.append(self.dcTitle)
        if self.dcDate:
            dcDate = keyProto + 'dc.date'
            keys.append(dcDate); values.append(self.dcDate.strftime(AssetProvenance.FMT_DATE))
        dcPublisher = keyProto + 'dc.publisher'
        keys.append(dcPublisher); values.append(self.dcPublisher)
        dcDescription = keyProto + 'dc.description'
        keys.append(dcDescription); values.append(self.dcDescription)
        GenericMetadata.writeProvenanceEntries(projectDir, keys, values)
    
    @classmethod
    def readFromMetadata(cls, projectDir, fqId):
        """ Read AssetProvenance data from provenance section of metadata for
            a given project directory
        
            @param projectDir String representing the path of the project whose metadata store is to be read from
            @param fqId String representing the fully qualified ID of the asset: <section>_<name>
            
            @return A new AssetProvenance instance with data populated from metadata
            
            @raise KeyError if required field is not in metadata
        """
        newInstance = AssetProvenance()
        (newInstance.section, newInstance.name) = fqId.split(GenericMetadata.COMPOUND_KEY_SEP)
        
        provenance = GenericMetadata.readProvenanceEntries(projectDir)
        keyProto = fqId + GenericMetadata.COMPOUND_KEY_SEP
        dcIdentifier = keyProto + 'dc.identifier'
        newInstance.dcIdentifier = provenance[dcIdentifier]
        dcSource = keyProto + 'dc.source'
        newInstance.dcSource = provenance[dcSource]
        dcTitle = keyProto + 'dc.title'
        newInstance.dcTitle = provenance[dcTitle]
        dcDate = keyProto + 'dc.date'
        newInstance.dcDate = datetime.strptime(provenance[dcDate], AssetProvenance.FMT_DATE)
        dcPublisher = keyProto + 'dc.publisher'
        newInstance.dcPublisher = provenance[dcPublisher]
        dcDescription = keyProto + 'dc.description'
        newInstance.dcDescription = provenance[dcDescription]
        
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
    COMPOUND_KEY_SEP = '/' # Used for keys that may contain KEY_SEP
    METADATA_FILENAME = 'metadata.txt'
    METADATA_LOCKFILE = 'metadata.txt.lock'
    
    MANIFEST_SECTION = 'manifest'
    PROVENANCE_SECTION = 'provenance'
    HISTORY_SECTION = 'history'
    STUDY_AREA_SECTION = 'study_area'
    CLIMATE_POINT_SECTION = 'climate_point'
    CLIMATE_GRID_SECTION = 'climate_grid'
    SECTIONS = [MANIFEST_SECTION, PROVENANCE_SECTION, HISTORY_SECTION,\
                STUDY_AREA_SECTION, CLIMATE_POINT_SECTION, CLIMATE_GRID_SECTION]
    
    HISTORY_PROTO = "processing%sstep%s" % (KEY_SEP, KEY_SEP)

    @staticmethod
    def writeEntryToSection(projectDir, section, key, value):
        """ Write an entry in the given section to the metadata store for a given project. 
        
            @note Will overwrite the value for a key that already exists
            
            @param projectDir Path of the project whose metadata store is to be written to
            @param section The section the key is to be written to
            @param key The key to be written to the given section of the project metadata
            @param value The value to be written for key stored in the given section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
            @exception Exception if section is not a valid GenericMetadata section
        """
        if section not in GenericMetadata.SECTIONS:
            raise Exception( "%s is an unknown section" % (section,) )
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
    def getCommandLine():
        """ Return string representing original command line, as close as possible,
            used to run the command.  Will convert all paths in the command line to
            absolute path, if a non-path element has spaces in it, they will be
            quoted.
            
            @return String with each element of sys.argv separated by a space
        """
        import sys, os
        cmdline = os.path.abspath(sys.argv[0]) + ' '
        for elem in sys.argv[1:]:
            if os.path.exists(elem):
                cmdline += os.path.abspath(elem) + ' '
            else:
                if elem.find(' ') != -1:
                    # If a non-path element has spaces in it, quote them
                    cmdline += '"' + elem + '"' + ' '
                else:
                    cmdline += elem + ' '
        return cmdline 
        
        
    @staticmethod
    def _writeEntriesToSection(projectDir, section, keys, values):
        """ Write entries in the given section to the metadata store for a given project. 
        
            @note Will overwrite the value for each key that already exists
            
            @param projectDir Path of the project whose metadata store is to be written to
            @param section The section the keys are to be written to
            @param keys List of keys to be written to the given section of the project metadata
            @param values List of values to be written for key stored in the given section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
            @exception Exception if len(keys) != len(values)
        """
        numKeys = len(keys)
        if numKeys != len(values):
            raise Exception( "%d keys specified for %d values" % (numKeys, len(values)) )
        
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
        # Write new entries
        if not config.has_section(section):
            config.add_section(section)
        for i in xrange(numKeys):
            config.set(section, keys[i], values[i])
        # Write metadata store
        config.write(open(metadataFilepath, 'w'))
        
        # Remove lock file
        os.unlink(lockFilepath)
    
    
    @staticmethod
    def writeManifestEntry(projectDir, key, value):
        """ Write a manifest entry to the metadata store for a given project.
            
            @note Will overwrite the value for a key that already exists
        
            @param projectDir Path of the project whose metadata store is to be written to
            @param key The key to be written to the manifest section of the project metadata
            @param value The value to be written for key stored in the manifest section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.writeEntryToSection(projectDir, GenericMetadata.MANIFEST_SECTION, key, value)
     
        
    @staticmethod 
    def writeStudyAreaEntry(projectDir, key, value):
        """ Write a study area entry to the metadata store for a given project.
            
            @note Will overwrite the value for a key that already exists
        
            @param projectDir Path of the project whose metadata store is to be written to
            @param key The key to be written to the study area section of the project metadata
            @param value The value to be written for key stored in the study area section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.writeEntryToSection(projectDir, GenericMetadata.STUDY_AREA_SECTION, key, value)
    
    
    @staticmethod 
    def writeClimatePointEntry(projectDir, key, value):
        """ Write a point climate entry to the metadata store for a given project.
            
            @note Will overwrite the value for a key that already exists
        
            @param projectDir Path of the project whose metadata store is to be written to
            @param key The key to be written to the point climate section of the project metadata
            @param value The value to be written for key stored in the point climate section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.writeEntryToSection(projectDir, GenericMetadata.CLIMATE_POINT_SECTION, key, value)
        
        
    @staticmethod 
    def writeClimatePointEntries(projectDir, keys, values):
        """ Write a point climate entries to the metadata store for a given project.
            
            @note Will overwrite the value for keys that already exist
        
            @param projectDir Path of the project whose metadata store is to be written to
            @param keys List of keys to be written to the point climate section of the project metadata
            @param values List of values to be written for keys stored in the point climate section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
            @exception Exception if len(keys) != len(values)
        """
        GenericMetadata._writeEntriesToSection(projectDir, GenericMetadata.CLIMATE_POINT_SECTION, keys, values)
    
    
    @staticmethod 
    def writeClimateGridEntry(projectDir, key, value):
        """ Write a grid climate entry to the metadata store for a given project.
            
            @note Will overwrite the value for a key that already exists
        
            @param projectDir Path of the project whose metadata store is to be written to
            @param key The key to be written to the grid climate  section of the project metadata
            @param value The value to be written for key stored in the grid climate  section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.writeEntryToSection(projectDir, GenericMetadata.CLIMATE_GRID_SECTION, key, value)
        
        
    @staticmethod 
    def writeClimateGridEntries(projectDir, keys, values):
        """ Write grid climate entries to the metadata store for a given project.
            
            @note Will overwrite the value for keys that already exist
        
            @param projectDir Path of the project whose metadata store is to be written to
            @param key List of keys to be written to the grid climate  section of the project metadata
            @param value List of values to be written for keys stored in the grid climate  section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
            @exception Exception if len(keys) != len(values)
        """
        GenericMetadata._writeEntriesToSection(projectDir, GenericMetadata.CLIMATE_GRID_SECTION, keys, values)
    
    
    @staticmethod 
    def writeProvenanceEntry(projectDir, key, value):
        """ Write a provenance entry to the metadata store for a given project.
            
            @note Will overwrite a the value for a key that already exists
        
            @param projectDir Path of the project whose metadata store is to be written to
            @param key The key to be written to the provenance section of the project metadata
            @param value The value to be written for key stored in the provenance section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.writeEntryToSection(projectDir, GenericMetadata.PROVENANCE_SECTION, key, value)
    
    @staticmethod 
    def writeProvenanceEntries(projectDir, keys, values):
        """ Write provenance entries to the metadata store for a given project.
            
            @note Will overwrite the values of keys that already exist
        
            @param projectDir Path of the project whose metadata store is to be written to
            @param keys The keys to be written to the provenance section of the project metadata
            @param values The values to be written for keys stored in the provenance section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
            @exception Exception if len(keys) != len(values)
        """
        GenericMetadata._writeEntriesToSection(projectDir, GenericMetadata.PROVENANCE_SECTION, keys, values)
    
    
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
        try:
            stations = climatePoints['stations'].split(GenericMetadata.VALUE_DELIM)
            for station in stations:
                stationObjects.append(ClimatePointStation.readFromMetadata(projectDir, station))
        except KeyError:
            pass
        return stationObjects
    
    
    @staticmethod
    def readClimateGridEntries(projectDir):
        """ Read all grid climate entries from the metadata store for a given project
        
            @param projectDir Absolute path of the project whose metadata are to be read
            
            @return A dictionary of key/value pairs from the grid climate section of the project metadata
        """
        return GenericMetadata._readEntriesForSection(projectDir, GenericMetadata.CLIMATE_GRID_SECTION)


    @staticmethod
    def readProvenanceEntries(projectDir):
        """ Read all provenance entries from the metadata store for a given project
        
            @param projectDir Absolute path of the project whose metadata are to be read
            
            @return A dictionary of key/value pairs from the provenance section of the project metadata
        """
        return GenericMetadata._readEntriesForSection(projectDir, GenericMetadata.PROVENANCE_SECTION)


    @staticmethod
    def readAssetProvenanceObjects(projectDir):
        """ Read all asset provenance objects from metadata and store in AssetProvenance
            instances.
            
            @param projectDir Absolute path of the project whose metadata are to be read
            
            @return A list of AssetProvenance objects
        """
        assetProvenanceObjects = []
        provenance = GenericMetadata.readProvenanceEntries(projectDir)
        try:
            assets = provenance['entities'].split(GenericMetadata.VALUE_DELIM)
            for asset in assets:
                assetProvenanceObjects.append(AssetProvenance.readFromMetadata(projectDir, asset))
        except KeyError:
            pass
        return assetProvenanceObjects
    
    
    @staticmethod
    def getProcessingHistoryList(projectDir):
        steps = []
        history = GenericMetadata._readEntriesForSection(projectDir, GenericMetadata.HISTORY_SECTION)
        try:
            idx = int(history['numsteps']) + 1
            for i in xrange(1, idx):
                key = GenericMetadata.HISTORY_PROTO + str(i)
                steps.append(history[key])
        except KeyError:
            pass
        
        return steps
    
    @staticmethod
    def appendProcessingHistoryItem(projectDir, item):
        history = GenericMetadata._readEntriesForSection(projectDir, GenericMetadata.HISTORY_SECTION)
        try:
            idx = int(history['numsteps'])
        except KeyError:
            idx = 0
        idx += 1
        
        idxStr = str(idx)
        key = GenericMetadata.HISTORY_PROTO + idxStr
        GenericMetadata._writeEntriesToSection(projectDir, GenericMetadata.HISTORY_SECTION, [key, 'numsteps'], [item, idxStr])
        
        