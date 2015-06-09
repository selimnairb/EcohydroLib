"""@package ecohydrolib.metadata
    
@brief Classes for writing and reading metadata for Ecohydrology workflows

This software is provided free of charge under the New BSD License. Please see
the following license information:

Copyright (c) 2013-2015, University of North Carolina at Chapel Hill
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

import ecohydrolib
import ecohydrolib.util

class MetadataEntity(object):
    
    FMT_DATE = '%Y-%m-%d %H:%M:%S'
    
    """ Abstract class for encoding structured data to be written to a metadata store
    """
    def writeToMetadata(self, context):
        """ Write structured entity to metadata store for a given project directory
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
        """
        pass
    
    @classmethod
    def readFromMetadata(cls, context, fqId):
        """ Read structured entity from metadata store for a given project directory
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            @param fqId String representing the fully qualified ID of the entity
            
            Implementations should return an instance of themselves containing data read from the metadata store
            
            @raise KeyError if entity is not in metadata
        """
        pass


class ClimatePointStation(MetadataEntity):
    
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
        
    def writeToMetadata(self, context):
        """ Write ClimatePointStation data to climate point section of metadata for
            a given project directory
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
        """
        fqId = self.type + GenericMetadata.COMPOUND_KEY_SEP + self.id
        fqId = fqId.lower()

        climatePoints = GenericMetadata.readClimatePointEntries(context)
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
        GenericMetadata.writeClimatePointEntries(context, keys, values)
    
    @classmethod
    def readFromMetadata(cls, context, fqId):
        """ Read ClimatePointStation data from climate point section of metadata for
            a given project directory
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            @param fqId String representing the fully qualified station ID: <type>_<id>
            
            @return A new ClimatePointStation instance with data populated from metadata
            
            @raise KeyError if required field is not in metadata
        """
        newInstance = ClimatePointStation()
        (newInstance.type, newInstance.id) = fqId.split(GenericMetadata.COMPOUND_KEY_SEP)

        climate = GenericMetadata.readClimatePointEntries(context)
        
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


class ModelRun(MetadataEntity):

    def __init__(self, modelType=None):
        self.modelType = modelType
        self.runNumber = None
        self.description = None
        self.date = None
        self.command = None
        self.output = None
        
    def writeToMetadata(self, context):
        """ Write ModelRun data to model run section of metadata for
            a given project directory
            
            @note Will set run number to value to be stored in metadata
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
            @exception Exception if model type has not known
            @exception Exception if section is not a valid GenericMetadata section
        """
        if self.modelType not in GenericMetadata.MODEL_TYPES:
            raise Exception("Model type %s is not among known model types: %s" % (self.modelType, str(GenericMetadata.MODEL_TYPES) ) )
        
        modelRunEntries = GenericMetadata.readModelRunEntries(context)
        try:
            runs = modelRunEntries['runs'].split(GenericMetadata.VALUE_DELIM)
        except KeyError:
            runs = []
        
        # Collected model entry and keys and values into lists so we can write to metadata store in batch
        keys = []
        values = []
            
        # Generate unique identifier for this model run.  Unique ID is a combination of model type and a number
        entryNumber = 1
        fqId = self.modelType + GenericMetadata.KEY_SEP + str(entryNumber)
        while fqId in runs:
            entryNumber += 1
            fqId = self.modelType + GenericMetadata.KEY_SEP + str(entryNumber)
        self.runNumber = entryNumber
        # Add new run to list of runs
        runs.append(fqId)
        runsStr = GenericMetadata.VALUE_DELIM.join(runs)
        keys.append('runs'); values.append(runsStr)
        # Write attributes for run
        keyProto = fqId + GenericMetadata.KEY_SEP
        runDate = keyProto + 'date_utc'
        keys.append(runDate); values.append( self.date.strftime(ModelRun.FMT_DATE) )
        runDesc = keyProto + 'description'
        keys.append(runDesc); values.append(self.description)
        runCmd = keyProto + 'command'
        keys.append(runCmd); values.append(self.command)
        runOutput = keyProto + 'output'
        keys.append(runOutput); values.append(self.output)
        # Write to metadata
        GenericMetadata.writeModelRunEntries(context, keys, values)
        
    @classmethod
    def readFromMetadata(cls, context, fqId):
        """ Read ModelRun data from model run section of metadata for
            a given project directory
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            @param fqId String representing the fully qualified ID of the model run: <model_type>_<run_number>
            
            @return A new ModelRun instance with data populated from metadata
            
            @raise KeyError if required field is not in metadata
        """      
        newInstance = ModelRun()
        (newInstance.modelType, newInstance.runNumber) = fqId.split(GenericMetadata.KEY_SEP)
        
        modelRunEntries = GenericMetadata.readModelRunEntries(context)
        keyProto = fqId + GenericMetadata.KEY_SEP
        
        runDate = keyProto + 'date_utc'
        newInstance.date = datetime.strptime(modelRunEntries[runDate], ModelRun.FMT_DATE)
        runDesc = keyProto + 'description'
        newInstance.description = modelRunEntries[runDesc]
        runCmd = keyProto + 'command'
        newInstance.command = modelRunEntries[runCmd]
        runOutput = keyProto + 'output'
        newInstance.output = modelRunEntries[runOutput]
        
        return newInstance
    

class AssetProvenance(MetadataEntity):
    
    def __init__(self, section=None):
        self.section = section
        self.name = None
        self.dcIdentifier = None
        self.dcSource = None
        self.dcTitle = None
        self.dcDate = datetime.now()
        self.dcPublisher = None
        self.dcDescription = None
        self.processingNotes = None
        
    def writeToMetadata(self, context):
        """ Write AssetProvenance data to provenance section of metadata for
            a given project directory
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
            @exception Exception if section is not a valid GenericMetadata section
        """
        fqId = self.section + GenericMetadata.COMPOUND_KEY_SEP + self.name
        fqId = fqId.lower()
        
        # Write self to the appropriate section
        GenericMetadata.writeEntryToSection(context, self.section, self.name, self.dcIdentifier)
        
        # Write to provenance section
        provenanceEntries = GenericMetadata.readProvenanceEntries(context)
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
        processingNotes = keyProto + 'processing_notes'
        keys.append(processingNotes); values.append(self.processingNotes)
        GenericMetadata.writeProvenanceEntries(context, keys, values)
    
    @classmethod
    def readFromMetadata(cls, context, fqId):
        """ Read AssetProvenance data from provenance section of metadata for
            a given project directory
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            @param fqId String representing the fully qualified ID of the asset: <section>_<name>
            
            @return A new AssetProvenance instance with data populated from metadata
            
            @raise KeyError if required field is not in metadata
        """
        newInstance = AssetProvenance()
        (newInstance.section, newInstance.name) = fqId.split(GenericMetadata.COMPOUND_KEY_SEP)
        
        provenance = GenericMetadata.readProvenanceEntries(context)
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
        processingNotes = keyProto + 'processing_notes'
        newInstance.processingNotes = provenance[processingNotes]
        
        return newInstance
    

class MetadataVersionError(ConfigParser.Error):
    def __init__(self, metadataVersion):
        self.metadataVersion = metadataVersion
        self._ecohydrolibVersion = ecohydrolib.__version__
    def __str__(self):
        return repr("Version %s of EcohydroLib was used to write the metadata, but you are running version %s of EcohydroLib" %\
                    (self.metadataVersion, self._ecohydrolibVersion) )    

class GenericMetadata(object):
    """ Handles metadata persistance.
    
        @note All keys are stored in lower case.
        @note This object is stateless, all methods are static, writes to metadata store
        are written immediately.
        
        @todo Implement lock file semantics as decorators
    """
    _ecohydrolibVersion = ecohydrolib.__version__

    VALUE_DELIM = ','
    KEY_SEP = '_'
    COMPOUND_KEY_SEP = '/' # Used for keys that may contain KEY_SEP
    METADATA_FILENAME = 'metadata.txt'
    METADATA_LOCKFILE = 'metadata.txt.lock'
    VERSION_KEY = 'ecohydrolib_version'
    
    ECOHYDROLIB_SECION = 'ecohydrolib'
    MANIFEST_SECTION = 'manifest'
    PROVENANCE_SECTION = 'provenance'
    HISTORY_SECTION = 'history'
    STUDY_AREA_SECTION = 'study_area'
    GRASS_SECTION = 'grass'
    CLIMATE_POINT_SECTION = 'climate_point'
    CLIMATE_GRID_SECTION = 'climate_grid'
    MODEL_RUN_SECTION = 'model_run'
    HYDROSHARE_SECTION = 'hydroshare'
    SECTIONS = [ECOHYDROLIB_SECION, MANIFEST_SECTION, PROVENANCE_SECTION, HISTORY_SECTION,
                STUDY_AREA_SECTION, GRASS_SECTION, CLIMATE_POINT_SECTION, CLIMATE_GRID_SECTION,
                MODEL_RUN_SECTION, HYDROSHARE_SECTION]
    
    HISTORY_PROTO = "processing%sstep%s" % (KEY_SEP, KEY_SEP)

    # Raster type list (this should probably be a dict)
    RASTER_TYPE_LC = 'landcover'
    RASTER_TYPE_ROOF = 'roof_connectivity'
    RASTER_TYPE_SOIL = 'soil'
    RASTER_TYPE_LAI = 'lai'
    RASTER_TYPE_PATCH = 'patch'
    RASTER_TYPE_ZONE = 'zone'
    RASTER_TYPE_ISOHYET = 'isohyet'
    RASTER_TYPE_LEAFC = 'leafc'
    RASTER_TYPE_ROOTDEPTH = 'rootdepth'
    RASTER_TYPE_ROAD = 'roads'
    RASTER_TYPE_STREAM_BURNED_DEM = 'stream_burned_dem'
    RASTER_TYPES = [RASTER_TYPE_LC, RASTER_TYPE_ROOF, RASTER_TYPE_SOIL, RASTER_TYPE_LAI, 
                    RASTER_TYPE_PATCH, RASTER_TYPE_ZONE, RASTER_TYPE_ISOHYET,
                    RASTER_TYPE_LEAFC, RASTER_TYPE_ROOTDEPTH, RASTER_TYPE_ROAD,
                    RASTER_TYPE_STREAM_BURNED_DEM]

    # Model type list
    MODEL_TYPES = []

    @staticmethod
    def getCommandLine():
        """ Return string representing original command line, as close as possible,
            used to run the command.  Will convert all paths in the command line to
            absolute path, if a non-path element has spaces in it, they will be
            quoted.
            
            @return String with each element of sys.argv separated by a space
        """
        import sys, os
        cmdline = os.path.abspath(sys.argv[0])
        for elem in sys.argv[1:]:
            cmdline += ' ' + ecohydrolib.util.getAbsolutePathOfItem(elem)
        return cmdline 


    @staticmethod
    def checkMetadataVersion(projectDir):
        """ Check if metadata store is compatible with current version of ecohydrolib. Accepts
            project directory as this method is used in the constructor to the Context class.
        
            @param projectDir, the path of the project whose metadata store is to be written to
            @raise MetadataVersionError if a version already exists in the metadata store
            and is different than GenericMetadata._ecohydrolibVersion
        """
        metadataFilepath = os.path.join(projectDir, GenericMetadata.METADATA_FILENAME)
        if os.path.exists(metadataFilepath):
            if not os.access(metadataFilepath, os.R_OK):
                raise IOError(errno.EACCES, "Unable to read metadata store for project %s" % \
                              (projectDir,))
            # Read metadata store
            config = ConfigParser.RawConfigParser()
            config.read(metadataFilepath)
            if config.has_section(GenericMetadata.ECOHYDROLIB_SECION):
                if config.has_option(GenericMetadata.ECOHYDROLIB_SECION, \
                                 GenericMetadata.VERSION_KEY):
                    metadataVersion = config.get(GenericMetadata.ECOHYDROLIB_SECION, \
                                     GenericMetadata.VERSION_KEY)
                    if metadataVersion != GenericMetadata._ecohydrolibVersion:
                        raise MetadataVersionError(metadataVersion)


    @staticmethod
    def _writeVersionToMetadata(config):
        """ Write EcohydroLib version to ECOHYDROLIB_SECION of metadata.
        
            @param config ConfigParser to write version information to
            @raise MetadataVersionError if a version already exists in the metadata store
            and is different than GenericMetadata._ecohydrolibVersion
        """
        if not config.has_section(GenericMetadata.ECOHYDROLIB_SECION):
            config.add_section(GenericMetadata.ECOHYDROLIB_SECION)
        
        if not config.has_option(GenericMetadata.ECOHYDROLIB_SECION, \
                             GenericMetadata.VERSION_KEY):
            config.set(GenericMetadata.ECOHYDROLIB_SECION, \
                       GenericMetadata.VERSION_KEY, GenericMetadata._ecohydrolibVersion)
            return
            
        metadataVersion = config.get(GenericMetadata.ECOHYDROLIB_SECION, \
                                     GenericMetadata.VERSION_KEY)
        if metadataVersion != GenericMetadata._ecohydrolibVersion:
            raise MetadataVersionError(metadataVersion)
        
    
    @staticmethod
    def deleteEntryFromSection(context, section, key, callback=None):
        """ Delete an entry from the given section of the metadata store for a given project.
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be deleted from
            @param section The section the key is to be deleted from
            @param key The key to be deleted from the given section of the project metadata
            @param callback A function that should be called before deleting the entry.  The function takes as
            input the config object.
        
            @raise IOError(errno.EACCES) if the metadata store for the project is not writable
            @raise Exception if section is not a valid GenericMetadata section
            @raise MetadataVersionError if existing version information in metadata store
            does not match version of currently running EcohydroLib.
        """
        projectDir = context.projectDir
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
        GenericMetadata._writeVersionToMetadata(config)
        
        if callback:
            callback(config)
        
        # Delete entry
        if config.has_section(section):
            config.remove_option(section, key)
            # Write metadata store
            config.write(open(metadataFilepath, 'w'))
        
        # Remove lock file
        os.unlink(lockFilepath)
    
    
    @staticmethod
    def writeEntryToSection(context, section, key, value, callback=None):
        """ Write an entry in the given section to the metadata store for a given project. 
        
            @note Will overwrite the value for a key that already exists
            
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
            @param section The section the key is to be written to
            @param key The key to be written to the given section of the project metadata
            @param value The value to be written for key stored in the given section of the project metadata
            @param callback A function that should be called before writing the entry.  The function takes as
            input the config object.
            
            @raise IOError(errno.EACCES) if the metadata store for the project is not writable
            @raise Exception if section is not a valid GenericMetadata section
            @raise MetadataVersionError if existing version information in metadata store
            does not match version of currently running EcohydroLib.
        """
        projectDir = context.projectDir
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
        GenericMetadata._writeVersionToMetadata(config)
        
        if callback:
            callback(config)
        
        # Write new entry
        if not config.has_section(section):
            config.add_section(section)
        config.set(section, key, value)
        # Write metadata store
        config.write(open(metadataFilepath, 'w'))
        
        # Remove lock file
        os.unlink(lockFilepath)
        
        
    @staticmethod
    def _writeEntriesToSection(projectDir, section, keys, values, callback=None):
        """ Write entries in the given section to the metadata store for a given project. 
        
            @note Will overwrite the value for each key that already exists
            
            @param projectDir Path of the project whose metadata store is to be written to
            @param section The section the keys are to be written to
            @param keys List of keys to be written to the given section of the project metadata
            @param values List of values to be written for key stored in the given section of the project metadata
            @param callback A function that should be called before writing the entry.  The function takes as
            input the config object.
            
            @raise IOError(errno.EACCES) if the metadata store for the project is not writable
            @raise Exception if len(keys) != len(values)
            @raise MetadataVersionError if existing version information in metadata store
            does not match version of currently running EcohydroLib.
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
        GenericMetadata._writeVersionToMetadata(config)
        
        if callback:
            callback(config)
        
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
    def writeManifestEntry(context, key, value):
        """ Write a manifest entry to the metadata store for a given project.
            
            @note Will overwrite the value for a key that already exists
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
            @param key The key to be written to the manifest section of the project metadata
            @param value The value to be written for key stored in the manifest section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.writeEntryToSection(context, GenericMetadata.MANIFEST_SECTION, key, value)
     
        
    @staticmethod 
    def writeStudyAreaEntry(context, key, value):
        """ Write a study area entry to the metadata store for a given project.
            
            @note Will overwrite the value for a key that already exists
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
            @param key The key to be written to the study area section of the project metadata
            @param value The value to be written for key stored in the study area section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.writeEntryToSection(context, GenericMetadata.STUDY_AREA_SECTION, key, value)
    
    
    @staticmethod 
    def writeGRASSEntry(context, key, value):
        """ Write a GRASS entry to the metadata store for a given project.  Typically used to 
            record the location within a project directory of a GRASS location and mapset, as well
            as to note the existence of particular datasets stored in the mapset
            
            @note Will overwrite the value for a key that already exists
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
            @param key The key to be written to the GRASS section of the project metadata
            @param value The value to be written for key stored in the GRASS section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.writeEntryToSection(context, GenericMetadata.GRASS_SECTION, key, value)
    
    
    @staticmethod 
    def writeClimatePointEntry(context, key, value):
        """ Write a point climate entry to the metadata store for a given project.
            
            @note Will overwrite the value for a key that already exists
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
            @param key The key to be written to the point climate section of the project metadata
            @param value The value to be written for key stored in the point climate section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.writeEntryToSection(context, GenericMetadata.CLIMATE_POINT_SECTION, key, value)
        
        
    @staticmethod 
    def writeClimatePointEntries(context, keys, values):
        """ Write a point climate entries to the metadata store for a given project.
            
            @note Will overwrite the value for keys that already exist
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
            @param keys List of keys to be written to the point climate section of the project metadata
            @param values List of values to be written for keys stored in the point climate section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
            @exception Exception if len(keys) != len(values)
        """
        GenericMetadata._writeEntriesToSection(context.projectDir, GenericMetadata.CLIMATE_POINT_SECTION, keys, values)
    
    
    @staticmethod 
    def writeClimateGridEntry(context, key, value):
        """ Write a grid climate entry to the metadata store for a given project.
            
            @note Will overwrite the value for a key that already exists
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            @param key The key to be written to the grid climate  section of the project metadata
            @param value The value to be written for key stored in the grid climate  section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.writeEntryToSection(context, GenericMetadata.CLIMATE_GRID_SECTION, key, value)
    
    
    @staticmethod 
    def writeHydroShareEntry(context, key, value):
        """ Write a HydroShare entry to the metadata store for a given project.
            
            @note Will overwrite the value for a key that already exists
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
            @param key The key to be written to the study area section of the project metadata
            @param value The value to be written for key stored in the HydroShare section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.writeEntryToSection(context, GenericMetadata.HYDROSHARE_SECTION, key, value)
        
    
    @staticmethod
    def deleteManifestEntry(context, key):
        """ Delete an entry from the manifest section of the metadata store for a given project.
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be deleted from
            @param key The key to be deleted from the given section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.deleteEntryFromSection(context, GenericMetadata.MANIFEST_SECTION, key)
     
        
    @staticmethod 
    def deleteStudyAreaEntry(context, key):
        """ Delete an entry from the study area section of the metadata store for a given project.
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be deleted from
            @param key The key to be deleted from the given section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.deleteEntryFromSection(context, GenericMetadata.STUDY_AREA_SECTION, key)
    
    
    @staticmethod 
    def deleteGRASSEntry(context, key):
        """ Delete an entry from the GRASS section of the metadata store for a given project.
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be deleted from
            @param key The key to be deleted from the given section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.deleteEntryFromSection(context, GenericMetadata.GRASS_SECTION, key)
    
    
    @staticmethod 
    def deleteClimatePointEntry(context, key):
        """ Delete an entry from the point climate section of the metadata store for a given project.
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be deleted from
            @param key The key to be deleted from the given section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.deleteEntryFromSection(context, GenericMetadata.CLIMATE_POINT_SECTION, key)
        
    
    @staticmethod 
    def deleteClimateGridEntry(context, key):
        """ Delete an entry from the grid climate section of the metadata store for a given project.
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be deleted from
            @param key The key to be deleted from the given section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.deleteEntryFromSection(context, GenericMetadata.CLIMATE_GRID_SECTION, key)
    
    
    @staticmethod 
    def deleteHydroShareEntry(context, key):
        """ Delete an entry from the HydroShare section of the metadata store for a given project.
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be deleted from
            @param key The key to be deleted from the given section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.deleteEntryFromSection(context, GenericMetadata.HYDROSHARE_SECTION, key)
    
        
    @staticmethod 
    def writeClimateGridEntries(context, keys, values):
        """ Write grid climate entries to the metadata store for a given project.
            
            @note Will overwrite the value for keys that already exist
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            @param key List of keys to be written to the grid climate  section of the project metadata
            @param value List of values to be written for keys stored in the grid climate  section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
            @exception Exception if len(keys) != len(values)
        """
        GenericMetadata._writeEntriesToSection(context.projectDir, GenericMetadata.CLIMATE_GRID_SECTION, keys, values)
    
    
    @staticmethod 
    def writeProvenanceEntry(context, key, value):
        """ Write a provenance entry to the metadata store for a given project.
            
            @note Will overwrite a the value for a key that already exists
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
            @param key The key to be written to the provenance section of the project metadata
            @param value The value to be written for key stored in the provenance section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
        """
        GenericMetadata.writeEntryToSection(context, GenericMetadata.PROVENANCE_SECTION, key, value)
    
    
    @staticmethod 
    def writeModelRunEntries(context, keys, values):
        """ Write model run entries to the metadata store for a given project.
            
            @note Will overwrite the values of keys that already exist
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
            @param keys The keys to be written to the model run section of the project metadata
            @param values The values to be written for keys stored in the model run section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
            @exception Exception if len(keys) != len(values)
        """
        GenericMetadata._writeEntriesToSection(context.projectDir, GenericMetadata.MODEL_RUN_SECTION, keys, values)
    
    
    @staticmethod 
    def writeProvenanceEntries(context, keys, values):
        """ Write provenance entries to the metadata store for a given project.
            
            @note Will overwrite the values of keys that already exist
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
            @param keys The keys to be written to the provenance section of the project metadata
            @param values The values to be written for keys stored in the provenance section of the project metadata
            
            @exception IOError(errno.EACCES) if the metadata store for the project is not writable
            @exception Exception if len(keys) != len(values)
        """
        GenericMetadata._writeEntriesToSection(context.projectDir, GenericMetadata.PROVENANCE_SECTION, keys, values)
    
    
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
    def readManifestEntries(context):
        """ Read all manifest entries from the metadata store for a given project
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            @return A dictionary of key/value pairs from the manifest section of the project metadata
        """
        return GenericMetadata._readEntriesForSection(context.projectDir, GenericMetadata.MANIFEST_SECTION)
    
    
    @staticmethod
    def readStudyAreaEntries(context):
        """ Read all study area entries from the metadata store for a given project
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            
            @return A dictionary of key/value pairs from the study area section of the project metadata
        """
        return GenericMetadata._readEntriesForSection(context.projectDir, GenericMetadata.STUDY_AREA_SECTION)
    
    
    @staticmethod
    def readGRASSEntries(context):
        """ Read all GRASS entries from the metadata store for a given project
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            
            @return A dictionary of key/value pairs from the GRASS section of the project metadata
        """
        return GenericMetadata._readEntriesForSection(context.projectDir, GenericMetadata.GRASS_SECTION)
    
    
    @staticmethod
    def readModelRunEntries(context):
        """ Read all point model run entries from the metadata store for a given project
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            @return A dictionary of key/value pairs from the model run section of the project metadata
        """
        return GenericMetadata._readEntriesForSection(context.projectDir, GenericMetadata.MODEL_RUN_SECTION)
    
    
    @staticmethod
    def readModelRuns(context):
        """ Read all model runs from metadata and store in ModelRun 
            instances.
            
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            @return A list of ModelRun objects
        """
        modelRunObjects = []
        modelRuns = GenericMetadata.readModelRunEntries(context)
        try:
            runs = modelRuns['runs'].split(GenericMetadata.VALUE_DELIM)
            for run in runs:
                modelRunObjects.append(ModelRun.readFromMetadata(context, run))
        except KeyError:
            pass
        return modelRunObjects

    
    @staticmethod
    def readClimatePointEntries(context):
        """ Read all point climate entries from the metadata store for a given project
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            @return A dictionary of key/value pairs from the point climate section of the project metadata
        """
        return GenericMetadata._readEntriesForSection(context.projectDir, GenericMetadata.CLIMATE_POINT_SECTION)
    
    
    @staticmethod
    def readClimatePointStations(context):
        """ Read all climate point stations from metadata and store in ClimatePointStation 
            instances.
            
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            @return A list of ClimatePointStation objects
        """
        stationObjects = []
        climatePoints = GenericMetadata.readClimatePointEntries(context)
        try:
            stations = climatePoints['stations'].split(GenericMetadata.VALUE_DELIM)
            for station in stations:
                stationObjects.append(ClimatePointStation.readFromMetadata(context, station))
        except KeyError:
            pass
        return stationObjects
    
    
    @staticmethod
    def readClimateGridEntries(context):
        """ Read all grid climate entries from the metadata store for a given project
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            
            @return A dictionary of key/value pairs from the grid climate section of the project metadata
        """
        return GenericMetadata._readEntriesForSection(context.projectDir, GenericMetadata.CLIMATE_GRID_SECTION)

    
    @staticmethod
    def readHydroShareEntries(context):
        """ Read all HydroShare entries from the metadata store for a given project
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            
            @return A dictionary of key/value pairs from the study area section of the project metadata
        """
        return GenericMetadata._readEntriesForSection(context.projectDir, GenericMetadata.HYDROSHARE_SECTION)


    @staticmethod
    def readProvenanceEntries(context):
        """ Read all provenance entries from the metadata store for a given project
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            
            @return A dictionary of key/value pairs from the provenance section of the project metadata
        """
        return GenericMetadata._readEntriesForSection(context.projectDir, GenericMetadata.PROVENANCE_SECTION)


    @staticmethod
    def readAssetProvenanceObjects(context):
        """ Read all asset provenance objects from metadata and store in AssetProvenance
            instances.
            
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be read from
            
            @return A list of AssetProvenance objects
        """
        assetProvenanceObjects = []
        provenance = GenericMetadata.readProvenanceEntries(context)
        try:
            assets = provenance['entities'].split(GenericMetadata.VALUE_DELIM)
            for asset in assets:
                assetProvenanceObjects.append(AssetProvenance.readFromMetadata(context, asset))
        except KeyError:
            pass
        return assetProvenanceObjects
    
    
    @staticmethod
    def getProcessingHistoryList(context):
        """ Get processing history stored in the project metadata
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
            @return List containing strings representing history items
        """
        projectDir = context.projectDir
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
    def appendProcessingHistoryItem(context, item):
        """ Write an item to the processing history stored in the project metadata
        
            @param context Context object containing projectDir, the path of the project whose 
            metadata store is to be written to
            @param item String representing item to be written to processing history
        """
        projectDir = context.projectDir
        history = GenericMetadata._readEntriesForSection(projectDir, GenericMetadata.HISTORY_SECTION)
        try:
            idx = int(history['numsteps'])
        except KeyError:
            idx = 0
        idx += 1
        
        idxStr = str(idx)
        key = GenericMetadata.HISTORY_PROTO + idxStr
        GenericMetadata._writeEntriesToSection(projectDir, GenericMetadata.HISTORY_SECTION, [key, 'numsteps'], [item, idxStr])
        
        