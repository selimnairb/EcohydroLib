"""@package ecohydroworkflowlib.tests.test_manifest_and_studyarea
    
    @brief Test methods for ecohydrologyworkflowlib.metadata
    
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
    
    Usage: 
    @code
    python -m unittest test_metadata
    @endcode
    
""" 
from unittest import TestCase
import os

from ecohydroworkflowlib.metadata import GenericMetadata

class TestManifestAndStudyArea(TestCase):
    
    def setUp(self):
        testMetadataPath = os.path.join("/tmp", GenericMetadata.METADATA_FILENAME)
        if os.path.exists(testMetadataPath):
            os.unlink(testMetadataPath)
        testMetadataPath = os.path.join("/tmp", GenericMetadata.METADATA_LOCKFILE)
        if os.path.exists(testMetadataPath):
            os.unlink(testMetadataPath)
    
    
    def test_empty_read(self):
        manifest = GenericMetadata.readManifestEntries("/tmp")
        self.assertTrue(len(manifest) == 0)
        
        studyArea = GenericMetadata.readStudyAreaEntries("/tmp")
        self.assertTrue(len(studyArea) == 0)
    
        climatePoint = GenericMetadata.readClimatePointEntries("/tmp")
        self.assertTrue(len(climatePoint) == 0)
        
        climateGrid = GenericMetadata.readClimateGridEntries("/tmp")
        self.assertTrue(len(climateGrid) == 0)
        
        
    def test_write_and_read(self):
        GenericMetadata.writeManifestEntry("/tmp", "key1", "value_one")
        GenericMetadata.writeManifestEntry("/tmp", "key2", "value_two")
        manifest = GenericMetadata.readManifestEntries("/tmp")
        self.assertTrue(manifest["key1"] == "value_one")
        
        GenericMetadata.writeStudyAreaEntry("/tmp", "key1", "value_one")
        GenericMetadata.writeStudyAreaEntry("/tmp", "key2", "value_two")
        studyArea = GenericMetadata.readStudyAreaEntries("/tmp")
        self.assertTrue(studyArea["key1"] == "value_one")
        
        GenericMetadata.writeClimatePointEntry("/tmp", "key1", "value_one")
        GenericMetadata.writeClimatePointEntry("/tmp", "key2", "value_two")
        climatePoint = GenericMetadata.readClimatePointEntries("/tmp")
        self.assertTrue(climatePoint["key1"] == "value_one")
        
        GenericMetadata.writeClimateGridEntry("/tmp", "key1", "value_one")
        GenericMetadata.writeClimateGridEntry("/tmp", "key2", "value_two")
        climateGrid = GenericMetadata.readClimateGridEntries("/tmp")
        self.assertTrue(climateGrid["key1"] == "value_one")
        