"""@package ecohydrolib.usgs.nlcdwcs
    
@brief Query NLCD datasets from WCS service provided by U.S. Geological Survey

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
import os, sys
import traceback

from owslib.wcs import WebCoverageService

FORMAT_GEOTIFF = 'GeoTIFF'
FORMATS = set([FORMAT_GEOTIFF])
MIME_TYPE = {FORMAT_GEOTIFF: 'image/GeoTIFF'}
FORMAT_EXT = {FORMAT_GEOTIFF: 'tif'}

URL_BASE = "http://raster.nationalmap.gov/arcgis/services/LandCover/USGS_EROS_LandCover_NLCD/MapServer/WCSServer"
DC_PUBLISHER = "http://raster.nationalmap.gov/arcgis/rest/services/LandCover/USGS_EROS_LandCover_NLCD/MapServer"

COVERAGES = {'Land_Cover_2011_AK_1': '1',
             'Land_Cover_2011_CONUS_2': '2',
             'Impervious_Surface_2011_CONUS_3': '3',
             'Canopy_2011_CONUS_4': '4',
             'Land_Cover_2006_CONUS_5': '5',
             'Impervious_Surface_2006_CONUS_6': '6',
             'Land_Cover_2001_AK_7': '7',
             'Land_Cover_2001_HI_8': '8',
             'Land_Cover_2001_PR_9': '9',
             'Land_Cover_2001_CONUS_10': '10',
             'Impervious_Surface_2001_AK_11': '11',
             'Impervious_Surface_2001_HI_12': '12',
             'Impervious_Surface_2001_CONUS_13': '13',
             'Impervious_Surface_2001_PR_14': '14',
             'Canopy_2001_AK_15': '15',
             'Canopy_2001_HI_16': '16',
             'Canopy_2001_CONUS_17': '17',
             'Canopy_2001_PR_18': '18',
             'Land_Cover_1992_19': '19' 
            }
USER_COVERAGES = {'Land_Cover_2011_CONUS_2': '2',
                  'Land_Cover_2006_CONUS_5': '5'}
LC_TYPE_TO_COVERAGE = {'NLCD2006': 'Land_Cover_2006_CONUS_5', 
                       'NLCD2011': 'Land_Cover_2011_CONUS_2'}
DEFAULT_COVERAGE = 'Land_Cover_2011_CONUS_2'

INTERPOLATION_METHODS = {'near': 'NEAREST'}

def getNLCDRasterDataForBoundingBox(config, outputDir, bbox, 
                                    coverage=DEFAULT_COVERAGE,
                                    filename='NLCD',
                                    srs='EPSG:4326',
                                    resx=0.000277777777778,
                                    resy=0.000277777777778,
                                    interpolation='near',
                                    fmt=FORMAT_GEOTIFF, 
                                    overwrite=False,
                                    verbose=False,
                                    outfp=sys.stdout):
    """
        Download NLCD rasters from 
        http://raster.nationalmap.gov/arcgis/rest/services/LandCover/USGS_EROS_LandCover_NLCD/MapServer
        
        @param config A Python ConfigParser (not currently used)
        @param outputDir String representing the absolute/relative path of the directory into which output raster should be written
        @param bbox Dict representing the lat/long coordinates and spatial reference of the bounding box area
            for which the raster is to be extracted.  The following keys must be specified: minX, minY, maxX, maxY, srs.
        @param srs String representing the spatial reference of the raster to be returned.
        @param resx Float representing the X resolution of the raster(s) to be returned
        @param resy Float representing the Y resolution of the raster(s) to be returned
        @param interpolation String representing resampling method to use. Must be one of spatialdatalib.utils.RASTER_RESAMPLE_METHOD.
        @param fmt String representing format of raster file.  Must be one of FORMATS.
        @param overwrite Boolean True if existing data should be overwritten
        @param verbose Boolean True if detailed output information should be printed to outfp
        @param outfp File-like object to which verbose output should be printed
    
        @return A dictionary mapping soil property names to soil property file path and WCS URL, i.e.
            dict[soilPropertyName] = (soilPropertyFilePath, WCS URL)
    
        @exception Exception if coverage is not known
        @exception Exception if interpolation method is not known
        @exception Exception if fmt is not a known format
        @exception Exception if output already exists by overwrite is False
    """
    if coverage not in COVERAGES:
        raise Exception("Coverage {0} is not known".format(coverage))
    if interpolation not in INTERPOLATION_METHODS:
        raise Exception("Interpolation method {0} is not of a known method {1}".format(interpolation,
                                                                                       INTERPOLATION_METHODS.keys()))
    if fmt not in FORMATS:
        raise Exception("Format {0} is not of a known format {1}".format(fmt, str(FORMATS)))
    if verbose:
        outfp.write("Acquiring NLCD coverage {lctype} from {pub}\n".format(lctype=coverage,
                                                                           pub=DC_PUBLISHER))
    
    outFilename = os.path.extsep.join([filename, FORMAT_EXT[fmt]])
    outFilepath = os.path.join(outputDir, outFilename)
        
    delete = False
    if os.path.exists(outFilepath):
        if not overwrite:
            raise Exception("File {0} already exists, and overwrite is false".format(outFilepath))
        else:
            delete = True
    
    try:
        if delete:
            os.unlink(outFilepath)
        
        wcs = WebCoverageService(URL_BASE, version='1.0.0')
        bbox = [bbox['minX'], bbox['minY'], bbox['maxX'], bbox['maxY']]
        wcsfp = wcs.getCoverage(identifier=COVERAGES[coverage], bbox=bbox,
                                crs=srs,
                                response_crs=srs,
                                resx=resx, # their WCS seems to accept resx, resy in meters
                                resy=resy,
                                format=fmt,
                                interpolation=INTERPOLATION_METHODS[interpolation])
        f = open(outFilepath, 'wb')
        f.write(wcsfp.read())
        f.close()
        
        return (True, URL_BASE, outFilename)
    except Exception as e:
        traceback.print_exc(file=outfp)
        raise(e)
    finally:
        # Clean-up
        pass
