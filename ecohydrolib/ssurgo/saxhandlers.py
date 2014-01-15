"""@package ecohydrolib.ssurgo.saxhandlers
    
@brief xml.sax.ContentHandler subclass for parsing SSURGO features stored as GML files

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
import xml.sax

from oset import oset

class SSURGOFeatureHandler(xml.sax.ContentHandler):
    """ Parse SSURGO features fetched from USDA soil datamart WFS 1.0.0 web service.
        Currently pulls out MUKEYs for each feature returned as either MapunitPoly or MapunitPolyExtended
        For example:
            /wfs:FeatureCollection/gml:featureMember/ms:MapunitPolyExtended/ms:MUKEY
            /wfs:FeatureCollection/gml:featureMember/ms:MapunitPoly/ms:MUKEY
        @note Parses with namespaces turned off. Parse also assumes XML is well-formed
    """
    wfs_FeatureCollection = "wfs:FeatureCollection"
    gml_featureMember = "gml:featureMember"
    ms_MapunitPoly = "ms:MapunitPoly"
    ms_MapunitPolyExtended = "ms:MapunitPolyExtended"
    ms_MUKEY = "ms:mukey"
    
    inWfsFeatureCollection = False
    inGmlFeatureMember = False
    inMapunitPolyExtended = False
    inMapunitPoly = False
    getMukey = False
    
    mukeys = None
    
    def __init__(self):
        """ Default constructor
            
            @param self This object
        """
        xml.sax.ContentHandler.__init__(self)
        self.mukeys = list()
        
    def characters(self, content):
        """ Called when character data are encountered
        
            @param self This object
            @param content String containing characters
        """
        if self.getMukey:
            #print "Saving MUKEY %s" % (content,)
            self.mukeys.append(content)
            
    def startElement(self, name, attrs):
        """ Called at the start of an element
        
            @param self This object
            @param name The name of the object
            @param attrs Attributes of the element
        """
        #print "startElement: " + name
        if (self.inMapunitPolyExtended or self.inMapunitPoly) and ( self.ms_MUKEY == name.lower() ):
            self.getMukey = True
        elif self.inGmlFeatureMember and (self.ms_MapunitPolyExtended == name):
            self.inMapunitPolyExtended = True
        elif self.inGmlFeatureMember and (self.ms_MapunitPoly == name):
            self.inMapunitPoly = True
        elif self.inWfsFeatureCollection and (self.gml_featureMember == name):
            self.inGmlFeatureMember = True
        elif self.wfs_FeatureCollection == name:
            self.inWfsFeatureCollection = True
            
            
    def endElement(self, name):
        """ Called at the end of an element
        
            @param self This object
            @param name The name of the object
        """
        if self.getMukey and (self.ms_MUKEY == name):
            self.getMukey = False
        elif self.inMapunitPolyExtended and (self.ms_MapunitPolyExtended == name):
            self.inMapunitPolyExtended = False
        elif self.inMapunitPoly and (self.ms_MapunitPoly == name):
            self.inMapunitPoly = False
        elif self.inGmlFeatureMember and (self.gml_featureMember == name):
            self.inGmlFeatureMember = False
        elif self.inWfsFeatureCollection and (self.wfs_FeatureCollection == name):
            self.inWfsFeatureCollection = False
            

class SSURGOMUKEYQueryHandler(xml.sax.ContentHandler):
    """ Parse query results fetched via USDA soil datamart tabular query web service.
        Query results are assumed to contain one or more attributes associated with MUKEYs.
        Supports results who contain multiple "rows" for a given MUKEY
    
        Stores results in a list of lists named "results". Each row is stored in the outer 
        list, with column values being stored in the inner list.
    
        Store column names in an ordered set (oset.oset) named "columnNames".
    
        @note Parses with namespaces turned off. Parse also assumes XML is well-formed.
          Assumes that the order of column names seen in the first row is
          the same order used for all rows. If this is not the case, columnNames
          will not represent the column names for all data in results.
    """
    NewDataSet = "NewDataSet"
    Table = "Table"
    mukey = "mukey"
    
    inNewDataSet = False
    inTable = False
    recordColData = False
    elementStack = None
    
    columnNames = None
    results = None
    
    _wroteResults = False
    _tmpColData = None
    
    def __init__(self):
        xml.sax.ContentHandler.__init__(self)
        self.results = list()
        self.elementStack = list()
        self.columnNames = oset()
        
    def characters(self, content):
        if self.recordColData:
            self.columnNames.add(self.elementStack[len(self.elementStack)-1])
            self._tmpColData.append(content) 
            self._wroteResults = True   
        
    def startElement(self, name, attrs):
        self.elementStack.append(name)
        
        if self.inTable:
            self.recordColData = True
        elif self.inNewDataSet and (self.Table == name):
            self.inTable = True
            self._tmpColData = list()
        elif self.NewDataSet == name:
            self.inNewDataSet = True
    
    def endElement(self, name):
        
        if self.recordColData and (self.elementStack[len(self.elementStack)-1] == name):
            if not self._wroteResults:
                # Handle case where attribute element was empty: make sure we write a blank string for the value
                self._tmpColData.append('')
            self.recordColData = False
            self._wroteResults = False
        elif self.inTable and (self.Table == name):
            self.inTable = False
            # Store column data
            self.results.append(self._tmpColData)
            self._tmpColData = None
        elif self.inNewDataSet and (self.NewDataSet == name):
            self.inNewDataSet = False
        
        self.elementStack.pop()
    