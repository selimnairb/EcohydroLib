"""@package ecohydroworkflowlib.tests.test_metadata
    
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
from datetime import datetime

from ecohydroworkflowlib.metadata import GenericMetadata
from ecohydroworkflowlib.metadata import ClimatePointStation
from ecohydroworkflowlib.metadata import AssetProvenance

class TestMetadata(TestCase):
    
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
        
        
    def test_write_climate_point1(self):
        """ Test case where there is a single data file the station """
        projectDir = "/tmp"
        station = ClimatePointStation()
        station.type = "GHCN"
        station.id = "US1MDBL0027"
        station.longitude = -76.716
        station.latitude = 39.317
        station.elevation = 128.0
        station.name = "My station name"
        station.data = "clim.txt"
        station.startDate = datetime.strptime("201007", "%Y%m")
        station.endDate = datetime.strptime("201110", "%Y%m")
        station.variables = [ClimatePointStation.VAR_PRECIP, \
                             ClimatePointStation.VAR_SNOW]
        station.writeToMetadata(projectDir)
        
        climatePointStation = GenericMetadata.readClimatePointStations(projectDir)[0]  
        self.assertTrue(station.type.lower() == climatePointStation.type)
        self.assertTrue(station.id.lower() == climatePointStation.id)
        self.assertTrue(station.longitude == climatePointStation.longitude)
        self.assertTrue(station.latitude == climatePointStation.latitude)
        self.assertTrue(station.elevation == climatePointStation.elevation)
        self.assertTrue(station.name == climatePointStation.name)
        self.assertTrue(station.data == climatePointStation.data)
        self.assertTrue(station.startDate == climatePointStation.startDate)
        self.assertTrue(station.endDate == climatePointStation.endDate)
        self.assertTrue(station.variables == climatePointStation.variables)
        
    def test_write_climate_point1_overwrite(self):
        """ Test case where there is a single data file the station, the entry is overwritten """
        projectDir = "/tmp"
        station = ClimatePointStation()
        station.type = "GHCN"
        station.id = "US1MDBL0027"
        station.longitude = -76.716
        station.latitude = 39.317
        station.elevation = 128.0
        station.name = "My station name"
        station.data = "clim.txt"
        station.startDate = datetime.strptime("201007", "%Y%m")
        station.endDate = datetime.strptime("201110", "%Y%m")
        station.variables = [ClimatePointStation.VAR_PRECIP, \
                             ClimatePointStation.VAR_SNOW]
        station.writeToMetadata(projectDir)
        
        climatePointStation = GenericMetadata.readClimatePointStations(projectDir)[0]  
        self.assertTrue(station.type.lower() == climatePointStation.type)
        self.assertTrue(station.id.lower() == climatePointStation.id)
        self.assertTrue(station.longitude == climatePointStation.longitude)
        self.assertTrue(station.latitude == climatePointStation.latitude)
        self.assertTrue(station.elevation == climatePointStation.elevation)
        self.assertTrue(station.name == climatePointStation.name)
        self.assertTrue(station.data == climatePointStation.data)
        self.assertTrue(station.startDate == climatePointStation.startDate)
        self.assertTrue(station.endDate == climatePointStation.endDate)
        self.assertTrue(station.variables == climatePointStation.variables)
        
        station.longitude = -76.716
        station.latitude = 39.317
        station.elevation = 128.0
        station.name = "My (longer) station name"
        station.data = "clim.dat"
        station.startDate = datetime.strptime("201006", "%Y%m")
        station.endDate = datetime.strptime("201310", "%Y%m")
        station.variables = [ClimatePointStation.VAR_PRECIP, \
                             ClimatePointStation.VAR_SNOW]
        station.writeToMetadata(projectDir)
        
        climatePointStation = GenericMetadata.readClimatePointStations(projectDir)[0]  
        self.assertTrue(station.type.lower() == climatePointStation.type)
        self.assertTrue(station.id.lower() == climatePointStation.id)
        self.assertTrue(station.longitude == climatePointStation.longitude)
        self.assertTrue(station.latitude == climatePointStation.latitude)
        self.assertTrue(station.elevation == climatePointStation.elevation)
        self.assertTrue(station.name == climatePointStation.name)
        self.assertTrue(station.data == climatePointStation.data)
        self.assertTrue(station.startDate == climatePointStation.startDate)
        self.assertTrue(station.endDate == climatePointStation.endDate)
        self.assertTrue(station.variables == climatePointStation.variables)
        
        
    def test_write_climate_point2(self):
        """ Test case where there are separate data files for each variable """
        projectDir = "/tmp"
        station = ClimatePointStation()
        station.type = "GHCN"
        station.id = "US1MDBL0027"
        station.longitude = -76.716
        station.latitude = 39.317
        station.elevation = 128.0
        station.name = "My station name"
        station.startDate = datetime.strptime("201007", "%Y%m")
        station.endDate = datetime.strptime("201110", "%Y%m")
        station.variables = [ClimatePointStation.VAR_PRECIP, \
                             ClimatePointStation.VAR_SNOW]
        station.variablesData[ClimatePointStation.VAR_PRECIP] = ClimatePointStation.VAR_PRECIP + '.txt'
        station.variablesData[ClimatePointStation.VAR_SNOW] = ClimatePointStation.VAR_SNOW + '.txt'
        station.writeToMetadata(projectDir)
        
        climatePointStation = GenericMetadata.readClimatePointStations(projectDir)[0]        
        self.assertTrue(station.type.lower() == climatePointStation.type)
        self.assertTrue(station.id.lower() == climatePointStation.id)
        self.assertTrue(station.longitude == climatePointStation.longitude)
        self.assertTrue(station.latitude == climatePointStation.latitude)
        self.assertTrue(station.elevation == climatePointStation.elevation)
        self.assertTrue(station.name == climatePointStation.name)
        self.assertTrue(station.startDate == climatePointStation.startDate)
        self.assertTrue(station.endDate == climatePointStation.endDate)
        self.assertTrue(station.variables == climatePointStation.variables)
        self.assertTrue(station.variablesData[ClimatePointStation.VAR_PRECIP] == climatePointStation.variablesData[ClimatePointStation.VAR_PRECIP])
        self.assertTrue(station.variablesData[ClimatePointStation.VAR_SNOW] == climatePointStation.variablesData[ClimatePointStation.VAR_SNOW])
        
    def test_provenance(self):
        """ Test case writing provenance metadata """
        projectDir = "/tmp"
        asset = AssetProvenance()
        asset.section = GenericMetadata.MANIFEST_SECTION
        asset.name = "dem"
        asset.dcIdentifier = "dem.tif"
        asset.dcSource = "http://www.demexplorer.com/..."
        asset.dcTitle = "Study area DEM"
        asset.dcDate = datetime.strptime("201303", "%Y%m")
        asset.dcPublisher = "USGS"
        asset.dcDescription = "RegisterDEM.py ..."
        asset.writeToMetadata(projectDir)
        
        assetProvenance = GenericMetadata.readAssetProvenanceObjects(projectDir)[0]
        self.assertTrue(asset.section == assetProvenance.section)
        self.assertTrue(asset.name == assetProvenance.name)
        self.assertTrue(asset.dcIdentifier == assetProvenance.dcIdentifier)
        self.assertTrue(asset.dcSource == assetProvenance.dcSource)
        self.assertTrue(asset.dcTitle == assetProvenance.dcTitle)
        self.assertTrue(asset.dcDate == assetProvenance.dcDate)
        self.assertTrue(asset.dcPublisher == assetProvenance.dcPublisher)
        self.assertTrue(asset.dcDescription == assetProvenance.dcDescription)
        
    def test_provenance_overwrite(self):
        """ Test case writing provenance metadata, with overwrite """
        projectDir = "/tmp"
        asset = AssetProvenance()
        asset.section = GenericMetadata.MANIFEST_SECTION
        asset.name = "dem"
        asset.dcIdentifier = "dem.tif"
        asset.dcSource = "http://www.demexplorer.com/..."
        asset.dcTitle = "Study area DEM"
        asset.dcDate = datetime.strptime("201303", "%Y%m")
        asset.dcPublisher = "USGS"
        asset.dcDescription = "RegisterDEM.py ..."
        asset.writeToMetadata(projectDir)
        
        assetProvenance = GenericMetadata.readAssetProvenanceObjects(projectDir)[0]
        self.assertTrue(asset.section == assetProvenance.section)
        self.assertTrue(asset.name == assetProvenance.name)
        self.assertTrue(asset.dcIdentifier == assetProvenance.dcIdentifier)
        self.assertTrue(asset.dcSource == assetProvenance.dcSource)
        self.assertTrue(asset.dcTitle == assetProvenance.dcTitle)
        self.assertTrue(asset.dcDate == assetProvenance.dcDate)
        self.assertTrue(asset.dcPublisher == assetProvenance.dcPublisher)
        self.assertTrue(asset.dcDescription == assetProvenance.dcDescription)
        
        asset.dcIdentifier = 'foo.img'
        asset.dcSource = "http://a.different.url/..."
        asset.dcTitle = "A different study area DEM"
        asset.dcDate = datetime.strptime("201304", "%Y%m")
        asset.dcPublisher = "NASA"
        asset.dcDescription = "GetDEMExplorerDEM.py ..."
        asset.writeToMetadata(projectDir)
        
        assetProvenance = GenericMetadata.readAssetProvenanceObjects(projectDir)[0]
        self.assertTrue(asset.section == assetProvenance.section)
        self.assertTrue(asset.name == assetProvenance.name)
        self.assertTrue(asset.dcIdentifier == assetProvenance.dcIdentifier)
        self.assertTrue(asset.dcSource == assetProvenance.dcSource)
        self.assertTrue(asset.dcTitle == assetProvenance.dcTitle)
        self.assertTrue(asset.dcDate == assetProvenance.dcDate)
        self.assertTrue(asset.dcPublisher == assetProvenance.dcPublisher)
        self.assertTrue(asset.dcDescription == assetProvenance.dcDescription)
        
        
    def test_processing_history(self):
        """ Test processing history metadata """
        projectDir = "/tmp"
        
        step1 = "mkdir foo; cd foo"
        step2 = "touch README.txt"
        step3 = "git init"
        
        GenericMetadata.appendProcessingHistoryItem(projectDir, step1)
        GenericMetadata.appendProcessingHistoryItem(projectDir, step2)
        GenericMetadata.appendProcessingHistoryItem(projectDir, step3)
        
        history = GenericMetadata.getProcessingHistoryList(projectDir)
        self.assertTrue(len(history) == 3, "Expected history length to be 3, but it is %d" % (len(history),) )
        self.assertTrue(history[0] == step1)
        self.assertTrue(history[1] == step2)
        self.assertTrue(history[2] == step3)
        