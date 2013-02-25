#!/usr/bin/env python
"""@package GHCNDSetup
    
@brief Builds SQLite3/Spatialite database for Query NCDC Global Historical Climatology Network 
station metadata downloaded from:
http://www1.ncdc.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt

@note Requires pyspatialite 2.6.2, spatialite 2.3.1; newer versions may break.

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
python2.7 ./GHCNDSetup.py -o <output_dir>
@endcode
"""
import os, sys, errno
import argparse
import ConfigParser
import urllib
import re
from pyspatialite import dbapi2 as spatialite


_sanitizeString = '[\'";]'

SRS = int(4326)
DB_NAME = 'GHCND.spatialite'
URL = 'http://www1.ncdc.noaa.gov/pub/data/ghcn/daily/ghcnd-stations.txt'

parser = argparse.ArgumentParser(description='Build database of GHCN station metadata')
parser.add_argument('-i', '--configfile', dest='configfile', required=True,
                    help='The configuration file')
parser.add_argument('-o', '--output', dest='outputDir', required=True,
                    help='Directory to which database named "GHCND.sqlite" should be placed')
parser.add_argument('-u', '--url', dest='url', required=False,
                    help='Override station metadata URL')
args = parser.parse_args()

config = ConfigParser.RawConfigParser()
config.read(args.configfile)

if not config.has_option('SPATIALITE', 'PATH_OF_INIT'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'SPATIALITE', 'PATH_OF_INIT'))

if not os.access(args.outputDir, os.W_OK):
    raise IOError(errno.EACCES, "Not allowed to write to output directory %s" %
                  args.outputDir)

spatialiteInitPath = config.get('SPATIALITE', 'PATH_OF_INIT')
ghcnDB = os.path.join(args.outputDir, DB_NAME)

url = URL
if args.url:
    url = args.url
    
# Delete DB if it already exists
if os.path.exists(ghcnDB):
    os.unlink(ghcnDB)
    
# 1. Create database
conn = spatialite.connect(ghcnDB)
cursor = conn.cursor()

# Setup spatial metadata
sys.stdout.write("Initializing spatial database...")
sqlFile = open(spatialiteInitPath, 'r')
for command in sqlFile:
    command = command.strip()
    
    if "BEGIN;" == command or "COMMIT;" == command or "VACUUM;" == command:
        # Ignore commands related to transactions as we are in a cursor
        continue

    cursor.execute(command)
sqlFile.close()

cursor.execute("""SELECT CheckSpatialMetaData()""")
hasSpatial = cursor.fetchone()[0] == 1
if not hasSpatial:
    sys.exit("Failed to create spatial metadata in table %s." % (ghcnDB,) )

# Create station table and indices
cursor.execute("""CREATE TABLE IF NOT EXISTS ghcn_station
(id TEXT NOT NULL PRIMARY KEY,
name TEXT,
elevation_m REAL)
""")
cursor.execute("""SELECT AddGeometryColumn('ghcn_station', 'coord', 4326, 'POINT', 2, 1)""")
cursor.execute("""SELECT CreateSpatialIndex('ghcn_station', 'coord')""")
sys.stdout.write("done\n")
sys.stdout.flush()

# 2. Fetch station metadata
sys.stdout.write("Downloading station data from NCDC (this may take a while)...")
f = urllib.urlopen(url)

# 3. Insert station metadata into database
line = f.readline()
while line:
    line.strip()
    #sys.stdout.write(line)
    id = unicode(line[:11].strip(), errors='replace')
    id = re.sub(_sanitizeString, '', id) # A poor substitute for proper escapeing, but SQLite3 python module sucks in this regard
    lat = float(line[12:19].strip())
    lon = float(line[21:29].strip())
    elev = float(line[31:36].strip())
    name = unicode(line[41:70].strip(), errors='replace')
    name = re.sub(_sanitizeString, '', name) # A poor substitute for proper escapeing, but SQLite3 python module sucks in this regard
    
    # SQLite can't handle parameter substitution within quotes (e.g. GeomFromText('POINT(:lon :lat)')
    #    cursor.execute("INSERT INTO ghcn_station (id,name,elevation_m,coord) VALUES (:id,:name,:elevation_m,GeomFromText('POINT(:lon :lat)', :srs) )",
    #                   {"id": id, "name": name, "elevation_m": elev, "lon": lon, "lat": lat, "srs": SRS})
    # So we have to do it the dangerous way ...
    sql = u"INSERT INTO ghcn_station (id,name,elevation_m,coord) VALUES ('%s','%s',%f,GeomFromText('POINT(%f %f)', %d) )" % \
        (id, name, elev, lon, lat, SRS)
    #print("sql to exec: %s\n" % (sql,) )
    cursor.execute(sql)
    
    line = f.readline()
    
conn.commit()
cursor.close()
conn.close()
sys.stdout.write("done\n")