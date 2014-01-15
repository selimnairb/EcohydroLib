"""@package ecohydrolib.ssurgo.attributequery
    
@brief Make tabular queries against USDA Soil Data Mart SOAP web service interface
@note Requires python-httplib2 to be installed, else requests to soil data mart may timeout

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
import cStringIO
import xml.sax
import json

import numpy as np
import socket
import httplib2
from oset import oset

from saxhandlers import SSURGOMUKEYQueryHandler

_BUFF_LEN = 4096 * 10

ATTRIBUTE_NAMESPACE = 'ms'
ATTRIBUTE_LIST = ['ksat', 'pctClay', 'pctSilt', 'pctSand', 'porosity',
                 'pmgroupname', 'texture', 'tecdesc', 'fieldCap', 
                 'avlWatCap']
ATTRIBUTE_LIST_NUMERIC = ['ksat', 'pctClay', 'pctSilt', 'pctSand', 'porosity', 
                        'fieldCap', 'avlWatCap']
# DERIVED_ATTRIBUTES must be a dictionary whose values are valid Python expressions combining members of ATTRIBUTE_LIST_NUMERIC
DERIVED_ATTRIBUTES = { 'drnWatCont': 'porosity - fieldCap' }
ATTRIBUTE_LIST_NUMERIC.extend( DERIVED_ATTRIBUTES.keys() )

def strListToString(strList):
    """ Converts a Python list of string values into a string containing quoted, 
        comma separated representation of the list.
        
        @param strList List of strings
        
        @return String containing quoted, comma separated representation of the list
    """
    numStr = len(strList)
    assert(numStr > 0)
    
    output = cStringIO.StringIO()
    for i in range(numStr - 1):
        output.write("'%s'," % (strList[i],))
    output.write("'%s'" % (strList[numStr-1],))
    
    returnStr = output.getvalue()
    output.close()
    return returnStr


def computeWeightedAverageKsatClaySandSilt(soilAttrTuple):
    """ Computes weighted average for Ksat, %clay/silt/sand for a SSURGO mukey based on values
        for each component in the mukey; weights based on component.comppct_r.
    
        @param soilAttrTuple Tuple returned from getParentMatKsatTexturePercentClaySiltSandForComponentsInMUKEYs
    
        @return Tuple containing: (1) a list containing column names; (2) a list of lists containing averaged soil properties for each mukey
    """
    data = list()
    representativeComponentDict = dict()
    derivedSet = oset()
    idx = 0
    
    # Convert numbers as text to numbers
    for row in soilAttrTuple[1]:
        mukey = int(row[0])
        comppct_r = int(row[2])
        try:
            maxRepComp = representativeComponentDict[mukey][1]
            if maxRepComp < comppct_r:
                representativeComponentDict[mukey] = (idx, comppct_r)
        except KeyError:
            representativeComponentDict[mukey] = (idx, comppct_r)
        try:
            hzdept_r = float(row[7])
        except ValueError:
            hzdept_r = -1
        try:
            ksat_r = float(row[8])
        except ValueError:
            ksat_r = -1
        try:
            claytotal_r = float(row[9])
        except ValueError:
            claytotal_r = -1
        try:
            silttotal_r = float(row[10])
        except ValueError:
            silttotal_r = -1
        try:
            sandtotal_r = float(row[11])
        except ValueError:
            sandtotal_r = -1
        try:
            wsatiated_r = float(row[12]) # a.k.a. porosity
        except ValueError:
            wsatiated_r = -1
        try:
            wthirdbar_r = float(row[13]) # a.k.a. field capacity
        except ValueError:
            wthirdbar_r = -1
        try:
            awc_r = float(row[14]) # a.k.a. plant available water capacity
        except ValueError:
            awc_r = -1
    
        data.append([mukey, row[1], comppct_r, row[3], row[4], row[5], row[6], hzdept_r, 
                     ksat_r, claytotal_r, silttotal_r, sandtotal_r, wsatiated_r,
                     wthirdbar_r, awc_r])
        idx = idx + 1

    mukeyCol = [row[0] for row in data]
    comppctCol = [row[2] for row in data]
    ksatCol = [row[8] for row in data]
    clayCol = [row[9] for row in data]
    siltCol = [row[10] for row in data]
    sandCol = [row[11] for row in data]
    porosityCol = [row[12] for row in data]
    fieldCapCol = [row[13] for row in data]
    availWaterCapCol = [row[14] for row in data]

    # Put values into Numpy 2-D array    
    npdata = np.array([mukeyCol, comppctCol, ksatCol, clayCol, siltCol, sandCol, 
                       porosityCol, fieldCapCol, availWaterCapCol]).transpose()
    # Remove duplicate rows 
    #   (which will arise because there can be multiple parent material groups for a given component)
    npdata = np.array([np.array(x) for x in set(tuple(x) for x in npdata)])
    # Register NoData values
    npdata = np.ma.masked_where(npdata == -1, npdata)

    # Calculate weighted average using component.comppct_r as weights
    avgSoilAttr = list()
    mukeySet = set(mukeyCol)
    for mukey in mukeySet:
        mySubSet = npdata[npdata[:,0] == mukey]
        myComppct = mySubSet[:,1]
        myKsat = mySubSet[:,2]
        myClay = mySubSet[:,3]
        mySilt = mySubSet[:,4]
        mySand = mySubSet[:,5]
        myPorosity = mySubSet[:,6]
        myFieldCap = mySubSet[:,7]
        myAvailWaterCap = mySubSet[:,8]
        # Calculate weighted averages, ignoring NoData values
        # These variable names MUST match values in ATTRIBUTE_LIST_NUMERIC
        ksat = np.ma.average(myKsat, weights=myComppct)
        pctClay = np.ma.average(myClay, weights=myComppct)
        pctSilt = np.ma.average(mySilt, weights=myComppct)
        pctSand = np.ma.average(mySand, weights=myComppct)
        porosity = np.ma.average(myPorosity, weights=myComppct)
        fieldCap = np.ma.average(myFieldCap, weights=myComppct)
        avlWatCap = np.ma.average(myAvailWaterCap, weights=myComppct)
        
        # Get modal value for qualitative values (pmgroupname, texture, tecdesc)
        maxRepIdx = representativeComponentDict[mukey][0]
        pmgroupname = data[maxRepIdx][3]
        texture = data[maxRepIdx][4]
        texdesc = data[maxRepIdx][5]
        
        attrList = [mukey, ksat, pctClay, pctSilt, pctSand, porosity, pmgroupname, texture, texdesc,
                    fieldCap, avlWatCap]
        # Generate derived variables
        for attr in DERIVED_ATTRIBUTES.keys():
            derivedAttr = eval( DERIVED_ATTRIBUTES[attr] )
            derivedSet.add(attr)
            attrList.append(derivedAttr) 
        
        avgSoilAttr.append(attrList)
    avgSoilHeaders = list(ATTRIBUTE_LIST)
    avgSoilHeaders.insert(0, 'mukey')
    for derived in derivedSet:
        print("Computed derived attribute %s = %s" % \
              (derived, DERIVED_ATTRIBUTES[derived]) )
        avgSoilHeaders.append(derived)
    
    return (avgSoilHeaders, avgSoilAttr)


def joinSSURGOAttributesToFeaturesByMUKEY_GeoJSON(geojson, typeName, ssurgoAttributes):
    """ Join SSURGO tabular attributes to MapunitPoly or MapunitPolyExtended features based on
        MUKEY.
    
        @param geojson JSON object representing SSURGO MapunitPolyExtended or MapunitPoly features
        @param typeName String of either 'MapunitPoly' or 'MapunitPolyExtended'
        @param ssurgoAttributes Tuple containing two lists: (1) list of column names; (2) list of
        column values.  Assumes the following column names and order:
        ['mukey', 'avgKsat', 'avgClay', 'avgSilt', 'avgSand', 'avgPorosity']
    
        @note geojson JSON object will be modified by this function   
    """
    assert(typeName == 'MapunitPoly' or typeName == 'MapunitPolyExtended')
    
    # Index attributes by MUKEY
    attributeDict = {}
    idx = 0
    for row in ssurgoAttributes[1]:
        myMukey = row[0]
        attributeDict[myMukey] = idx
        idx = idx + 1
        
    for feature in geojson['features']:
        properties = feature['properties']
        mukey = int(properties['mukey'])
        
        try:
            mukeyIdx = attributeDict[mukey]
        except KeyError:
            continue
        
        currAttrIdx = 1
        # Add attributes to this feature's properties table
        for attr in ssurgoAttributes[0][1:]:
            properties[attr] = str(ssurgoAttributes[1][mukeyIdx][currAttrIdx])
            currAttrIdx += 1
            

def getParentMatKsatTexturePercentClaySiltSandForComponentsInMUKEYs(mukeyList):
    """ Query USDA soil datamart tabular service for ksat, texture, % clay, % silt, % sand for all
        components in the specified map units.
    
        @param mukeyList List of strings representing the MUKEY of each map unit for which we would 
        like to query attributes.
    
        @return Tuple containing an ordered set (oset.oset) representing column names, and a list, 
        each element containing a list of column values for each row in the SSURGO query result for each map unit
        
        @raise socket.error if there was an error reading the data from the web service
        @raise Exception if webservice returned code other than 200
    """ 

    #client = SoapClient(wsdl="http://sdmdataaccess.nrcs.usda.gov/Tabular/SDMTabularService.asmx?WSDL")

    # Query to get component %, ksat_r, texture, texture description, parent material, horizon name, horizon depth,
    # %clay, %silt, %sand, and porosity (as wsatiated.r, volumetric SWC at or near 0 bar tension) for all components in an MUKEY
    # Will select first non-organic horizon (i.e. horizon names that do not start with O, L, or F)
    QUERY_PROTO = """SELECT c.mukey, c.cokey, c.comppct_r, p.pmgroupname, tg.texture, tg.texdesc, 
ch.hzname, ch.hzdept_r, ch.ksat_r, ch.claytotal_r, ch.silttotal_r, ch.sandtotal_r, ch.wsatiated_r,
ch.wthirdbar_r, ch.awc_r
FROM component c
LEFT JOIN copmgrp p ON c.cokey=p.cokey AND p.rvindicator='yes'
INNER JOIN chorizon ch ON c.cokey=ch.cokey 
AND ch.hzdept_r=(SELECT TOP(1) hzdept_r FROM chorizon WHERE cokey=c.cokey AND (hzname NOT LIKE 'O' + '%%') and (hzname NOT LIKE 'L' + '%%') and (hzname NOT LIKE 'F' + '%%') ORDER BY hzdept_r ASC)
LEFT JOIN chtexturegrp tg ON ch.chkey=tg.chkey AND tg.rvindicator='yes' AND tg.texture<>'variable' AND tg.texture<>'VAR'
WHERE c.mukey IN (%s) ORDER BY c.cokey"""
    
    mukeyStr = strListToString(mukeyList)
    
    query = QUERY_PROTO % mukeyStr
    
    # Manually make SOAP query (it's a long story)
    host = 'sdmdataaccess.nrcs.usda.gov'
    url = '/Tabular/SDMTabularService.asmx'
    url = "http://" + host + url
    
    soapQueryBegin = """<?xml version="1.0" encoding="UTF-8"?><soap:Envelope xmlns:soap="http://schemas.xmlsoap.org/soap/envelope/" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><soap:Header/><soap:Body>
    <RunQuery xmlns="http://SDMDataAccess.nrcs.usda.gov/Tabular/SDMTabularService.asmx">
    <Query>
    """
    soapQueryEnd = """</Query></RunQuery></soap:Body></soap:Envelope>"""
    
    soapQuery = soapQueryBegin + xml.sax.saxutils.escape(query) + soapQueryEnd
    
    headers = { 'SOAPAction': 'http://SDMDataAccess.nrcs.usda.gov/Tabular/SDMTabularService.asmx/RunQuery',  #'SOAPAction': 'RunQuery',
                'Content-Type': 'text/xml; charset=utf-8',
                'Content-length': str(len(soapQuery)) }
    h = httplib2.Http()
    res = None
    try:
        (res, content) = h.request(url, method='POST', body=soapQuery, headers=headers)
    except socket.error as e:
        raise e
    
    if 200 != res.status:
        raise Exception("Error %d encountered when reading SSURGO attributes from USDA webservice" % \
                        (res.status,) )

    # Parse results
    handler = SSURGOMUKEYQueryHandler()
    
    xml.sax.parseString(content, handler)

    return (handler.columnNames,handler.results)
    
