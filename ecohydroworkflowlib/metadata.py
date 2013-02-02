"""!@package ecohydroworkflowlib.metadata
    
@brief Methods for writing and reading metadata for Ecohydrology workflows

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

METADATA_FILENAME = 'metadata.txt'
METADATA_LOCKFILE = 'metadata.txt.lock'
MANIFEST_SECTION = 'MANIFEST'
STUDY_AREA_SECTION = 'STUDY_AREA'


def _writeEntryToSection(projectDir, section, key, value):
    """!Write a manifest entry to the metadata store for a given project. 
    
        @note Will blindly overwrite a the value for a key that already exists
        
        @param projectDir Path of the project whose metadata store is to be written to
        @param section The section the key is to be written to
        @param key The key to be written to the given section of the project metadata
        @param value The value to be written for key stored in the given section of the project metadata
        
        @exception IOError(errno.EACCES) if the metadata store for the project is not writable
    """
    lockFilepath = os.path.join(projectDir, METADATA_LOCKFILE)
    metadataFilepath = os.path.join(projectDir, METADATA_FILENAME)
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


def writeManifestEntry(projectDir, key, value):
    """!Write a manifest entry to the metadata store for a given project.
        
        @note Will blindly overwrite a the value for a key that already exists
    
        @param projectDir Path of the project whose metadata store is to be written to
        @param key The key to be written to the manifest section of the project metadata
        @param value The value to be written for key stored in the manifest section of the project metadata
        
        @exception IOError(errno.EACCES) if the metadata store for the project is not writable
    """
    _writeEntryToSection(projectDir, MANIFEST_SECTION, key, value)
    
    
def writeStudyAreaEntry(projectDir, key, value):
    """!Write a study area entry to the metadata store for a given project.
        
        @note Will blindly overwrite a the value for a key that already exists
    
        @param projectDir Path of the project whose metadata store is to be written to
        @param key The key to be written to the study area section of the project metadata
        @param value The value to be written for key stored in the study area section of the project metadata
        
        @exception IOError(errno.EACCES) if the metadata store for the project is not writable
    """
    _writeEntryToSection(projectDir, STUDY_AREA_SECTION, key, value)


def _readEntriesForSection(projectDir, section):
    """!Read all entries for the given section from the metadata store for a given project
    
        @param projectDir Absolute path of the project whose metadata are to be read
        @param section The section the key is to be written to
        
        @exception A dictionary of key/value pairs from the given section of the project metadata
    """
    sectionDict = dict()
    metadataFilepath = os.path.join(projectDir, METADATA_FILENAME)
    if os.path.exists(metadataFilepath):
        if not os.access(metadataFilepath, os.R_OK):
            raise IOError(errno.EACCES, "Unable to read metadata store for project %s" % \
                          (projectDir,))
        # Read metadata store
        config = ConfigParser.RawConfigParser()
        config.read(metadataFilepath)
        items = config.items(section)
        for item in items:
            sectionDict[item[0]] = item[1]
    
    return sectionDict


def readManifestEntries(projectDir):
    """!Read all manifest entries from the metadata store for a given project
    
        @param projectDir Absolute path of the project whose metadata are to be read
        
        @exception A dictionary of key/value pairs from the manifest section of the project metadata
    """
    return _readEntriesForSection(projectDir, MANIFEST_SECTION)


def readStudyAreaEntries(projectDir):
    """!Read all study area entries from the metadata store for a given project
    
        @param projectDir Absolute path of the project whose metadata are to be read
        
        @exception A dictionary of key/value pairs from the study area section of the project metadata
    """
    return _readEntriesForSection(projectDir, STUDY_AREA_SECTION)

