"""@package ecohydrolib.geosciaus.soilwcs
    
@brief Query soils data from WCS service provided by CSIRO/Geoscience Australia

This software is provided free of charge under the New BSD License. Please see
the following license information:

Copyright (c) 2015, University of North Carolina at Chapel Hill
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
import tempfile
import shutil

from owslib.wcs import WebCoverageService

FORMAT_GEOTIFF = 'GeoTIFF'
MIME_TYPE = {FORMAT_GEOTIFF: 'image/GeoTIFF'}

# VARIABLE = {'clay': 'CLY',
#             'silt': 'SLT',
#             'sand': 'SND'
#             }

VARIABLE = {'clay': 'CLY'}

URL_BASE = "http://www.asris.csiro.au/ArcGis/services/TERN/{variable}_ACLEP_AU_TRN_N/MapServer/WCSServer"

COVERAGES = ["{variable}_000_005_EV_N_P_AU_TRN_N_1",  # 0-5cm 
             "{variable}_005_015_EV_N_P_AU_TRN_N_4",  # 5-15cm
             "{variable}_015_030_EV_N_P_AU_TRN_N_7",  # 15-30cm
             "{variable}_030_060_EV_N_P_AU_TRN_N_10", # 30-60cm
             "{variable}_060_100_EV_N_P_AU_TRN_N_13", # 60-100cm
            ]

# Example URL: http://www.asris.csiro.au/ArcGis/services/TERN/CLY_ACLEP_AU_TRN_N/MapServer/WCSServer?SERVICE=WCS&VERSION=1.0.0&REQUEST=GetCoverage&COVERAGE=CLY_000_005_EV_N_P_AU_TRN_N_1&FORMAT=GeoTIFF&BBOX=147.539,-37.024,147.786,-36.830&RESX=0.000277777777778&RESY=0.000277777777778&CRS=EPSG:4283&RESPONSE_CRS=EPSG:4326&INTERPOLATION=bilinear&Band=1
# http://www.asris.csiro.au/ArcGis/services/TERN/CLY_ACLEP_AU_TRN_N/MapServer/WCSServer?SERVICE=WCS&REQUEST=GetCoverage&VERSION=1.0.0&COVERAGE=1&FORMAT=GeoTIFF&BBOX=147.539,-37.024,147.786,-36.830&RESX=0.000277777777778&RESY=0.000277777777778&CRS=EPSG:4283&RESPONSE_CRS=EPSG:4326&INTERPOLATION=bilinear&Band=1
# Clay: http://www.asris.csiro.au/ArcGis/services/TERN/CLY_ACLEP_AU_TRN_N/MapServer/WCSServer?SERVICE=WCS&REQUEST=GetCapabilities
# Silt: http://www.asris.csiro.au/ArcGis/services/TERN/SLT_ACLEP_AU_TRN_N/MapServer/WCSServer?SERVICE=WCS&REQUEST=GetCapabilities
# Sand: http://www.asris.csiro.au/ArcGis/services/TERN/SND_ACLEP_AU_TRN_N/MapServer/WCSServer?SERVICE=WCS&REQUEST=GetCapabilities

def _getCoverageIDsForCoverageTitle(wcs, variable):
    coverages = wcs.items()
    coverage_ids = {}
    for coverage in coverages:
        #print('id: %s, title %s' % (coverage[0], coverage[1].title))
        id = coverage[0]
        title = coverage[1].title
        for c in COVERAGES:
            c = c.format(variable=variable)
            if title == c:
                coverage_ids[c] = id
         
    return coverage_ids

def getSoilsRasterDataForBoundingBox(config, outputDir, bbox, srs='EPSG:4326', fmt=FORMAT_GEOTIFF, overwrite=True):
    """
    
    """
    tmpdir = tempfile.mkdtemp()
    print(tmpdir)
    
    for v in VARIABLE.keys():
        variable = VARIABLE[v]
        url = URL_BASE.format(variable=variable)

        wcs = WebCoverageService(url, version='1.0.0')
        coverages = _getCoverageIDsForCoverageTitle(wcs, variable)
        
        for c in coverages.keys():
            coverage = coverages[c]
            #coverage = c.format(variable=variable)
            wcsfp = wcs.getCoverage(identifier=coverage, bbox=bbox, format=fmt)
            filename = os.path.join(tmpdir, "{coverage}.tif".format(coverage=coverage))
            f = open(filename, 'wb')
            f.write(wcsfp.read())
            f.close()
            
    
    # Clean-up
    #shutil.rmtree(tmpdir)
        
        