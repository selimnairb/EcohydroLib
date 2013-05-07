#!/usr/bin/env python
"""@package DumpMetadataToiRODSXML

@brief Dump EcohydroLib metadata to iRODS XML metadata import format

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
  

Pre conditions:
--------------
1. Metadata exist for the specified project directory
   

Post conditions:
----------------
2. A file named metadata.xml will be written to the specified project directory

Usage:
@code
DumpMetadataToiRODSXML.py -p /path/to/project_dir -c /irods/collection/path
@endcode
"""
import os
import codecs
import argparse
from xml.sax.saxutils import escape

from ecohydrolib.context import Context
from ecohydrolib.metadata import GenericMetadata
from ecohydrolib.metadata import AssetProvenance


PATH_SEP_IRODS = '/'
OUTFILE_NAME = 'metadata.xml'

def writeAVUToXMLFile(outfile, target, attribute, value, unit=None):
    """ Write Attribute, Value, Unit (AVU) element to iRODS metadata XML file
    
        @param outfile StreamWriter representing the XML file. It is assumed that opening 
        <metadata> element has already been written to the file
        @param target String representing the contents of the Target element
        @param attribute String representing the contents of the Attribute element
        @param value String representing the contents of the Value element
        @param unit String representing the contents of the Unit element.  
        If None, an empty element will be written 
    """
    outfile.write('\t<AVU>\n')
    outfile.write("\t\t<Target>%s</Target>\n" % (escape(target),))
    outfile.write("\t\t<Attribute>%s</Attribute>\n" % (escape(attribute),) )
    outfile.write("\t\t<Value>%s</Value>\n" % (escape(value),) )
    if unit:
        outfile.write("\t\t<Unit>%s</Unit>\n" % (unit,) )
    else:
        outfile.write('\t\t<Unit />\n')
    outfile.write('\t</AVU>\n')

def writeDictToXMLFile(outfile, target, dict):
    """ Write the contents of a dict as AVU elements in an iRODS metadata XML file
    
        @param outfile StreamWriter representing the XML file. It is assumed that opening 
        <metadata> element has already been written to the file
        @param target String representing the contents of the Target element
        @param dict The dictionary whose key will serve as attributes and whose values will serve as
        values. Units will be written as empty elements for each AVU written
    """
    targetStr = "\t\t<Target>%s</Target>\n" % (escape(target),)
    for key in dict.keys():
        outfile.write('\t<AVU>\n')
        outfile.write(targetStr)
        outfile.write("\t\t<Attribute>%s</Attribute>\n" % (escape(key),) )
        outfile.write("\t\t<Value>%s</Value>\n" % (escape(dict[key]),) )
        outfile.write('\t\t<Unit />\n')
        outfile.write('\t</AVU>\n')


parser = argparse.ArgumentParser(description='Dump point climate station information from EcohydroLib metadata to standard output')
parser.add_argument('-p', '--projectDir', dest='projectDir', required=True,
                    help='The directory from which metadata should be read')
parser.add_argument('-c', '--collection', dest='collection', required=True,
                    help='The iRODS collection corresponding to the project directory')
args = parser.parse_args()

context = Context(args.projectDir, None) 

# Make sure there's no trailing PATH_SEP_IRODS on the collection
collection = args.collection.rstrip(PATH_SEP_IRODS)

outfilePath = os.path.join(context.projectDir, OUTFILE_NAME)
outfile = codecs.getwriter('utf-8')(open(outfilePath, 'w')) 
outfile.write('<?xml version="1.0" encoding="UTF-8" ?>\n')
outfile.write('<metadata>\n')

# Write study area metadata to collection root
writeDictToXMLFile(outfile,  collection, GenericMetadata.readStudyAreaEntries(context))

# Write processing history to collection root
history = GenericMetadata.getProcessingHistoryList(context)
i = 1
for entry in history:
    attribute = "processing_step_%d" % (i,); i += 1
    writeAVUToXMLFile(outfile, collection, attribute, entry)

# Write provenance to each item in the manifest
provenance = GenericMetadata.readAssetProvenanceObjects(context)
for entry in provenance:
    target = collection + PATH_SEP_IRODS + entry.dcIdentifier
    writeAVUToXMLFile(outfile, target, 'name', entry.name)
    writeAVUToXMLFile(outfile, target, 'dc.source', entry.dcSource)
    writeAVUToXMLFile(outfile, target, 'dc.title', entry.dcTitle)
    writeAVUToXMLFile(outfile, target, 'dc.date', entry.dcDate.strftime(AssetProvenance.FMT_DATE))
    writeAVUToXMLFile(outfile, target, 'dc.publisher', entry.dcPublisher)
    writeAVUToXMLFile(outfile, target, 'dc.description', entry.dcDescription)
    
# Write point climate station metadata to the data file for that station
stations = GenericMetadata.readClimatePointStations(context)
for station in stations:
    target = collection + PATH_SEP_IRODS + station.data
    writeAVUToXMLFile(outfile, target, 'id', station.id)
    writeAVUToXMLFile(outfile, target, 'name', station.name)
    writeAVUToXMLFile(outfile, target, 'longitude', str(station.longitude), 'WGS84 degrees')
    writeAVUToXMLFile(outfile, target, 'latitude', str(station.latitude), 'WGS84 degrees')
    writeAVUToXMLFile(outfile, target, 'elevation', str(station.elevation), 'meters')

outfile.write('</metadata>\n')
outfile.close()