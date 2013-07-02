#!/usr/bin/env python
"""@package NHDPlusV2Setup
    
@brief Builds SQLite3 databases from NHDPlus V2 data archives downloaded from
http://www.horizon-systems.com/NHDPlus/NHDPlusV2_home.php
@brief Assembles regional NHDPlus V2 data into national dataset suitable for gage-
reach based region of interest extraction

@note Requires GDAL/OGR that has been built with SQLite3 support
@note Requires 7z to extract data from archive files

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
NHDPlusSetup.py -i <config_file> -a  <archive_dir> -o <output_dir>
@endcode
"""
import os
import sys
import errno
import argparse
import subprocess
import sqlite3
import ConfigParser

from ecohydrolib.dbf import dbfreader


parser = argparse.ArgumentParser(description='Assemble regional NHDPLus V2 data into a national dataset')
parser.add_argument('-i', '--configfile', dest='configfile', required=True,
                    help='The configuration file')
parser.add_argument('-a', '--archive', dest='archiveDir', 
                    required=True,
                    help='Directory in which to look for NHDPLus V2 .7z archives')
parser.add_argument('-o', '--output', dest='outputDir', 
                    required=True,
                    help='Directory to which processed NHDPLus V2 data should be placed')
parser.add_argument('-s1', '--skipUnzip', dest='skipUnzip', action='store_true',
                    default=False, required=False,
                    help='Skip step where archives are unzipped to output directory')
parser.add_argument('-s2', '--skipCatchment', dest='skipCatchment', action='store_true',
                    default=False, required=False,
                    help='Skip step where regional catchment shapefiles are merged')
parser.add_argument('-s3', '--skipDB', dest='skipDB', action='store_true',
                    default=False, required=False,
                    help='Skip step where database is created')
parser.add_argument('-s4', '--skipGageLoc', dest='skipGageLoc', action='store_true',
                    default=False, required=False,
                    help='Skip step where GageLoc database is created')
args = parser.parse_args()

config = ConfigParser.RawConfigParser()
config.read(args.configfile)

if not config.has_option('GDAL/OGR', 'PATH_OF_OGR2OGR'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'GDAL/OGR', 'PATH_OF_OGR2OGR'))
if not config.has_option('UTIL', 'PATH_OF_FIND'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'UTIL', 'PATH_OF_FIND'))
if not config.has_option('UTIL', 'PATH_OF_SEVEN_ZIP'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'UTIL', 'PATH_OF_SEVEN_ZIP'))
if not config.has_option('UTIL', 'PATH_OF_SQLITE'):
    sys.exit("Config file %s does not define option %s in section %s" & \
          (args.configfile, 'UTIL', 'PATH_OF_SQLITE'))
    
pathOfOgr = config.get('GDAL/OGR', 'PATH_OF_OGR2OGR')
pathOfFind = config.get('UTIL', 'PATH_OF_FIND')
pathOfSevenZip = config.get('UTIL', 'PATH_OF_SEVEN_ZIP')
pathOfSqlite = config.get('UTIL', 'PATH_OF_SQLITE')

if not os.access(args.archiveDir, os.R_OK):
    raise IOError(errno.EACCES, "Not allowed to read from archive directory %s" %
                  args.archiveDir)

if not os.access(args.outputDir, os.W_OK):
    raise IOError(errno.EACCES, "Not allowed to write to output directory %s" %
                  args.outputDir)

nhdPlusDB = os.path.join(args.outputDir, "NHDPlusDB.sqlite")

# 0. Unpacking NHDPlus archives into output directory
if not args.skipUnzip:
    print("Unpacking NHDPlus archives into output directory %s" % (args.outputDir,))

    # Get a list of zip files
    zipFiles = subprocess.check_output("%s %s -type f -name *.7z -print" % (pathOfFind, args.archiveDir,), shell=True).split()

    # Unpack zip files into output directory
    for file in zipFiles:
        sevenZCommand = "%s x -y -o%s %s" % \
            (pathOfSevenZip, args.outputDir, file)
        print sevenZCommand
        returnCode = os.system(sevenZCommand)
        assert(returnCode == 0)

# 1. Find GageLoc shapefile and convert it to a spatial SQLite DB
if not args.skipGageLoc:
    print("Converting GageLoc shapefile to sqlite database ...")
    gageLocDB = os.path.join(args.outputDir, "GageLoc.sqlite")
    gageLoc = subprocess.check_output("%s %s -type f -iname GageLoc.shp -print" % (pathOfFind, args.outputDir,), shell=True).split()
    assert(gageLoc)
    gageLocShp = gageLoc[0]
    assert(os.access(gageLocShp, os.R_OK))
    ogrCommand = '%s -gt 65536 -f "SQLite" -t_srs "EPSG:4326" %s %s' % (pathOfFind, gageLocDB, gageLocShp)
    returnCode = os.system(ogrCommand)
    assert(returnCode == 0) 
    
    # Index fields
    sqliteCommand = "%s %s 'CREATE INDEX IF NOT EXISTS reachcode_measure_idx on GageLoc (reachcode,measure)'" % (pathOfSqlite, gageLocDB)
    returnCode = os.system(sqliteCommand)
    assert(returnCode == 0)
    
    sqliteCommand = "%s %s 'CREATE INDEX IF NOT EXISTS gage_loc_source_fea_idx ON GageLoc (source_fea)'" % (pathOfSqlite, gageLocDB)
    returnCode = os.system(sqliteCommand)
    assert(returnCode == 0)
    #cursor.execute("""""")
    

# 2. Find catchment shapefiles
if not args.skipCatchment:
    conusCatchment = os.path.join(args.outputDir, "Catchment.sqlite")
    #print conusCatchment

    # Remove existing conusCatchment
    if os.access(conusCatchment, os.F_OK):
        os.remove(conusCatchment)

    print("Finding catchment shapefiles")
    shapefiles = subprocess.check_output("%s %s -type f -iname Catchment.shp -print" % (pathOfFind, args.outputDir,), shell=True).split()
    #print shapefiles

    # 3. Intersect all catchment shapefiles into one shapefile for the entire CONUS
    print("Intersecting regional catchment shapefiles in to single CONUS catchment feature dataset ...")
    numFiles = len(shapefiles)
    currFile = 0
    for file in shapefiles:
        pctComplete = (float(currFile) / float(numFiles)) * 100
        currFile = currFile + 1
        ogrCommand = '%s -gt 65536 -f "SQLite" -append %s %s' % (pathOfOgr, conusCatchment, file)
        #print ogrCommand
        sys.stdout.write("\r\tProcessing file %d of %d (%.0f%%)" % (currFile, numFiles, pctComplete))
        sys.stdout.flush()
        returnCode = os.system(ogrCommand)
        assert(returnCode == 0)

    pctComplete = (float(currFile) / float(numFiles)) * 100
    sys.stdout.write("\r\tProcessing file %d of %d (%.0f%%)\n" % (currFile, numFiles, pctComplete))

    # 4. Add index to CONUS catchment
    print "Indexing CONUS shapefile (this may take a while) ..."
    sqliteCommand = "%s %s 'CREATE INDEX IF NOT EXISTS featureid_idx on catchment (featureid)'" % (pathOfSqlite, conusCatchment)
    returnCode = os.system(sqliteCommand)
    assert(returnCode == 0)

# 5. Create NHDPlus SQLite database to store flowline and stream gage records
if not args.skipDB:
    # Remove existing database if it's there
    if os.access(nhdPlusDB, os.F_OK):
        os.remove(nhdPlusDB)
    #conn = sqlite3.connect(nhdPlusDB, isolation_level=None)
    conn = sqlite3.connect(nhdPlusDB)
    cursor = conn.cursor()
    
    # Create PlusFlowlineVAA table and indices
    cursor.execute("""CREATE TABLE IF NOT EXISTS PlusFlowlineVAA
    (ComID INTEGER,
    Fdate DATETIME,
    StreamLeve INTEGER,
    StreamOrde INTEGER,
    StreamCalc INTEGER,
    FromNode INTEGER,
    ToNode INTEGER,
    Hydroseq INTEGER,
    LevelPathI INTEGER,
    Pathlength REAL,
    TerminalPa INTEGER,
    ArbolateSu REAL,
    Divergence INTEGER,
    StartFlag INTEGER,
    TerminalFl INTEGER,
    DnLevel INTEGER,
    ThinnerCod INTEGER,
    UpLevelPat INTEGER,
    UpHydroseq INTEGER,
    DnLevelPat INTEGER,
    DnMinorHyd INTEGER,
    DnDrainCou INTEGER,
    DnHydroseq INTEGER,
    FromMeas REAL,
    ToMeas REAL,
    ReachCode TEXT,
    LengthKM REAL,
    Fcode INTEGER,
    RtnDiv INTEGER,
    OutDiv INTEGER,
    DivEffect INTEGER,
    VPUIn INTEGER,
    VPUOut INTEGER,
    TravTime INTEGER,
    PathTime INTEGER,
    AreaSqKM REAL,
    TotDASqKM REAL,
    DivDASqKM REAL)
    """)
    cursor.execute("""CREATE INDEX IF NOT EXISTS PlusFlowlineVAA_Comid_idx ON PlusFlowlineVAA (ComID)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS PlusFlowlineVAA_Reachcode_idx ON PlusFlowlineVAA (ReachCode)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS PlusFlowlineVAA_FromMeas_idx ON PlusFlowlineVAA (FromMeas)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS PlusFlowlineVAA_ToMeas_idx ON PlusFlowlineVAA (ToMeas)""")
    
    # Create PlusFlow table and indices
    cursor.execute("""CREATE TABLE IF NOT EXISTS PlusFlow
    (FROMCOMID INTEGER,
    FROMHYDSEQ INTEGER,
    FROMLVLPAT INTEGER,
    TOCOMID INTEGER,
    TOHYDSEQ INTEGER,
    TOLVLPAT INTEGER,
    NODENUMBER INTEGER,
    DELTALEVEL INTEGER,
    DIRECTION INTEGER,
    GAPDISTKM REAL,
    HasGeo TEXT,
    TotDASqKM REAL,
    DivDASqKM REAL)
    """)
    cursor.execute("""CREATE INDEX IF NOT EXISTS plusflow_from_idx ON PlusFlow (FROMCOMID)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS plusflow_to_idx ON PlusFlow (TOCOMID)""")
    
    # Create Gage_Loc table and indices
    cursor.execute("""CREATE TABLE IF NOT EXISTS Gage_Loc
    (ComID INTEGER,
    EventDate DATETIME, 
    ReachCode TEXT,
    ReachSMDat INTEGER,
    Reachresol TEXT,
    FeatureCom INTEGER,
    FeatureCla INTEGER,
    Source_Ori TEXT,
    Source_Dat TEXT,
    Source_Fea TEXT,
    Featuredet TEXT,
    Measure REAL,
    Offset INTEGER,
    EventType TEXT)
    """)
    cursor.execute("""CREATE INDEX IF NOT EXISTS gage_loc_source_fea_idx ON Gage_Loc (Source_Fea)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS reachcode_measure_idx on Gage_Loc (ReachCode,Measure)""")
    
    # Create Gage_Info table
    # Gage_Info.GageID maps to Gage_Loc.Source_Fea
    cursor.execute("""CREATE TABLE IF NOT EXISTS Gage_Info
    (GageID TEXT,
    Agency_cd TEXT,
    Station_NM TEXT,
    State_CD TEXT,
    State TEXT,
    SiteStatus TEXT,
    DA_SQ_Mile REAL,
    Lon_Site REAL,
    Lat_Site REAL,
    Lon_NHD REAL,
    Lat_NHD REAL,
    Reviewed TEXT)
    """)
    cursor.execute("""CREATE INDEX IF NOT EXISTS gage_info_gageID_idx ON Gage_Info (GageID)""")
    
    # Create Gage_Smooth table
    # Gage_Smooth.SITE_NO maps to Gage_Info.GageID
    cursor.execute("""CREATE TABLE IF NOT EXISTS Gage_Smooth
    (SITE_NO TEXT,
    YEAR INTEGER,
    MO INTEGER,
    AVE REAL,
    COMPLETERE REAL)
    """)
    cursor.execute("""CREATE UNIQUE INDEX IF NOT EXISTS gage_smooth_idx ON Gage_Smooth (SITE_NO, YEAR, MO)""")
    
    # Create NHDReachCode_Comid table and indices
    cursor.execute("""CREATE TABLE IF NOT EXISTS NHDReachCode_Comid
    (COMID INTEGER,
    REACHCODE TEXT,
    REACHSMDAT DATETIME,
    RESOLUTION TEXT,
    GNIS_ID INTEGER,
    GNIS_NAME TEXT)
    """)
    cursor.execute("""CREATE INDEX IF NOT EXISTS NHDReachCode_Comid_Comid_idx ON NHDReachCode_Comid (COMID)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS NHDReachCode_Comid_Reachcode_idx ON NHDReachCode_Comid (REACHCODE)""")
    
    # Create NHDFlowline table and indices
    cursor.execute("""CREATE TABLE IF NOT EXISTS NHDFlowline
    (COMID INTEGER,
    FDATE DATETIME,
    RESOLUTION TEXT,
    GNIS_ID INTEGER,
    GNIS_NAME TEXT,
    LENGTHKM REAL,
    REACHCODE TEXT,
    FLOWDIR TEXT,
    WBAREACOMI INTEGER,
    FTYPE TEXT,
    FCODE INTEGER,
    SHAPE_LENG REAL,
    ENABLED TEXT,
    GNIS_NBR INTEGER)
    """)
    cursor.execute("""CREATE INDEX IF NOT EXISTS NHDFlowline_Comid_idx ON NHDReachCode_Comid (COMID)""")
    cursor.execute("""CREATE INDEX IF NOT EXISTS NHDFlowline_Reachcode_idx ON NHDReachCode_Comid (REACHCODE)""")
    
    cursor.close()
    
    # 5. Import NHDPlus data into SQLite database
    # Find PlusFlow.dbf files, open each, import into DB
    print("Importing regional PlusFlowlineVAA.dbf records into CONUS database (this will take a while) ...")
    cursor = conn.cursor()
    dbfs = subprocess.check_output("%s %s -type f -iname PlusFlowlineVAA.dbf -print" % (pathOfFind, args.outputDir,), shell=True).split()
    numFiles = len(dbfs)
    currFile = 0
    for file in dbfs:
        #print file
        pctComplete = (float(currFile) / float(numFiles)) * 100
        currFile = currFile + 1
        sys.stdout.write("\r\tProcessing file %d of %d (%.0f%%)" % (currFile, numFiles, pctComplete))
        sys.stdout.flush()
        f = open(file, 'rb')
        db = list(dbfreader(f))
        f.close()
        records = db[2:]
        for record in records:
            #print record
            cursor.execute("""INSERT INTO PlusFlowlineVAA
    (ComID,Fdate,StreamLeve,StreamOrde,StreamCalc,FromNode,ToNode,Hydroseq,LevelPathI,Pathlength,TerminalPa,ArbolateSu,Divergence,StartFlag,TerminalFl,DnLevel,ThinnerCod,UpLevelPat,UpHydroseq,DnLevelPat,DnMinorHyd,DnDrainCou,DnHydroseq,FromMeas,ToMeas,ReachCode,LengthKM,Fcode,RtnDiv,OutDiv,DivEffect,VPUIn,VPUOut,TravTime,PathTime,AreaSqKM,TotDASqKM,DivDASqKM)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (record[0], record[1].strftime("%Y-%m-%d %H:%M:%S"), record[2], record[3], record[4], record[5], record[6], record[7], record[8], float(record[9]), record[10], float(record[11]), record[12], record[13], record[14], record[15], record[16], record[17], record[18], record[19], record[20], record[21], record[22], float(record[23]), float(record[24]), unicode(record[25], errors='replace'), float(record[26]), record[27], record[28], record[29], record[30], record[31], record[32], float(record[33]), float(record[34]), float(record[35]), float(record[36]), float(record[37])))
    conn.commit()
    cursor.close()
    
    pctComplete = (float(currFile) / float(numFiles)) * 100
    sys.stdout.write("\r\tProcessing file %d of %d (%.0f%%)\n" % (currFile, numFiles, pctComplete)) 
    
    # Find PlusFlow.dbf files, open each, import into DB
    print("Importing regional PlusFlow.dbf records into CONUS database (this will take a while) ...")
    cursor = conn.cursor()
    dbfs = subprocess.check_output("%s %s -type f -iname PlusFlow.dbf -print" % (pathOfFind, args.outputDir,), shell=True).split()
    numFiles = len(dbfs)
    currFile = 0
    for file in dbfs:
        #print file
        pctComplete = (float(currFile) / float(numFiles)) * 100
        currFile = currFile + 1
        sys.stdout.write("\r\tProcessing file %d of %d (%.0f%%)" % (currFile, numFiles, pctComplete))
        sys.stdout.flush()
        f = open(file, 'rb')
        db = list(dbfreader(f))
        f.close()
        records = db[2:]
        for record in records:
            #print record
            cursor.execute("""INSERT INTO PlusFlow
    (FROMCOMID,FROMHYDSEQ,FROMLVLPAT,TOCOMID,TOHYDSEQ,TOLVLPAT,NODENUMBER,DELTALEVEL,DIRECTION,GAPDISTKM,HasGeo,TotDASqKM,DivDASqKM)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (record[0], record[1], record[2], record[3], record[4], record[5], record[6], record[7], record[8], float(record[9]), record[10], float(record[11]), float(record[12])))
    conn.commit()
    cursor.close()
    
    pctComplete = (float(currFile) / float(numFiles)) * 100
    sys.stdout.write("\r\tProcessing file %d of %d (%.0f%%)\n" % (currFile, numFiles, pctComplete)) 
    
    # Find NHDReachCode_Comid.dbf files, open each, import into DB    
    print("Importing regional NHDReachCode_Comid.dbf records into CONUS database (this will take a while) ...")
    cursor = conn.cursor()
    dbfs = subprocess.check_output("%s %s -type f -iname NHDReachCode_Comid.dbf -print" % (pathOfFind, args.outputDir,), shell=True).split()
    numFiles = len(dbfs)
    currFile = 0
    for file in dbfs:
        #print file
        pctComplete = (float(currFile) / float(numFiles)) * 100
        currFile = currFile + 1
        sys.stdout.write("\r\tProcessing file %d of %d (%.0f%%)" % (currFile, numFiles, pctComplete))
        sys.stdout.flush()
        f = open(file, 'rb')
        db = list(dbfreader(f))
        f.close()
        records = db[2:]
        for record in records:
            #print record
            cursor.execute("""INSERT INTO NHDReachCode_Comid
    (COMID,REACHCODE,REACHSMDAT,RESOLUTION,GNIS_ID,GNIS_NAME)
    VALUES (?,?,?,?,?,?)""",
            (record[0], unicode(record[1], errors='replace'), record[2].strftime("%Y-%m-%d %H:%M:%S"), unicode(record[3], errors='replace'), record[4], unicode(record[5], errors='replace')))
    conn.commit()
    cursor.close()
    
    pctComplete = (float(currFile) / float(numFiles)) * 100
    sys.stdout.write("\r\tProcessing file %d of %d (%.0f%%)\n" % (currFile, numFiles, pctComplete)) 
    
    # Find NHDFlowline.dbf files, open each, import into DB 
    print("Importing regional NHDFlowline.dbf records into CONUS database (this will take a while) ...")
    cursor = conn.cursor()
    dbfs = subprocess.check_output("%s %s -type f -iname NHDFlowline.dbf -print" % (pathOfFind, args.outputDir,), shell=True).split()
  
    numFiles = len(dbfs)
    currFile = 0
    for file in dbfs:
        #print file
        pctComplete = (float(currFile) / float(numFiles)) * 100
        currFile = currFile + 1
        sys.stdout.write("\r\tProcessing file %d of %d (%.0f%%)" % (currFile, numFiles, pctComplete))
        sys.stdout.flush()
        f = open(file, 'rb')
        db = list(dbfreader(f))
        f.close()
        records = db[2:]
        for record in records:
            #print record
            # Handle case where NHDFlowline record lacks GNIS_NBR attribute
            try:
                GNIS_NBR = record[13]
            except IndexError:
                GNIS_NBR = 0
            cursor.execute("""INSERT INTO NHDFlowline
    (COMID,FDATE,RESOLUTION,GNIS_ID,GNIS_NAME,LENGTHKM,REACHCODE,FLOWDIR,WBAREACOMI,FTYPE,FCODE,SHAPE_LENG,ENABLED,GNIS_NBR)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (record[0], record[1].strftime("%Y-%m-%d %H:%M:%S"), unicode(record[2], errors='replace'), record[3], unicode(record[4], errors='replace'), float(record[5]), unicode(record[6], errors='replace'), unicode(record[7], errors='replace'), record[8], unicode(record[9], errors='replace'), record[10], float(record[11]), unicode(record[12], errors='replace'), GNIS_NBR))
    conn.commit()
    cursor.close()
    
    pctComplete = (float(currFile) / float(numFiles)) * 100
    sys.stdout.write("\r\tProcessing file %d of %d (%.0f%%)\n" % (currFile, numFiles, pctComplete)) 
    
    # Find GageLoc.dbf file, import into DB 
    print("Importing national GageLoc.dbf ...")
    cursor = conn.cursor()
    dbf = subprocess.check_output("%s %s -type f -iname GageLoc.dbf -print" % (pathOfFind, args.outputDir,), shell=True).split()[0]
    assert(dbf)
    print dbf
    f = open(dbf, 'rb')
    db = list(dbfreader(f))
    f.close()
    records = db[2:]
    for record in records:
        #print record
        cursor.execute("""INSERT INTO Gage_Loc
    (ComID,EventDate,ReachCode,ReachSMDat,Reachresol,FeatureCom,FeatureCla,Source_Ori,Source_Dat,Source_Fea,Featuredet,Measure,Offset,EventType)
    VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (record[0], record[1].strftime("%Y-%m-%d %H:%M:%S"), unicode(record[2], errors='replace'), record[3], unicode(record[4], errors='replace'), record[5], record[6], unicode(record[7], errors='replace'), unicode(record[8], errors='replace'), unicode(record[9], errors='replace'), unicode(record[10], errors='replace'), float(record[11]), record[12], unicode(record[13], errors='replace')))
    conn.commit()
    cursor.close()
    
    # Find GageInfo.dbf file, import into DB 
    print("Importing national GageInfo.dbf ...")
    cursor = conn.cursor()
    dbf = subprocess.check_output("%s %s -type f -iname GageInfo.dbf -print" % (pathOfFind, args.outputDir,), shell=True).split()[0]
    assert(dbf)
    print dbf
    f = open(dbf, 'rb')
    db = list(dbfreader(f))
    f.close()
    records = db[2:]
    for record in records:
        #print record
        # Handle presence of undocumented NHD2DAGE_D field (if present)
        if len(record) > 12:
            cursor.execute("""INSERT INTO Gage_Info
        (GageID,Agency_cd,Station_NM,State_CD,State,SiteStatus,DA_SQ_Mile,Lon_Site,Lat_Site,Lon_NHD,Lat_NHD,Reviewed)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (unicode(record[0],errors='replace'), unicode(record[1], errors='replace'), unicode(record[2], errors='replace'), unicode(record[3], errors='replace'), unicode(record[4], errors='replace'), unicode(record[5], errors='replace'), float(record[6]), float(record[7]), float(record[8]), float(record[9]), float(record[10]), unicode(record[12], errors='replace') ))
        else:
            cursor.execute("""INSERT INTO Gage_Info
        (GageID,Agency_cd,Station_NM,State_CD,State,SiteStatus,DA_SQ_Mile,Lon_Site,Lat_Site,Lon_NHD,Lat_NHD,Reviewed)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?)""",
            (unicode(record[0],errors='replace'), unicode(record[1], errors='replace'), unicode(record[2], errors='replace'), unicode(record[3], errors='replace'), unicode(record[4], errors='replace'), unicode(record[5], errors='replace'), float(record[6]), float(record[7]), float(record[8]), float(record[9]), float(record[10]), unicode(record[11], errors='replace') ))
    conn.commit()
    cursor.close()
    
    # Find Gage_Smooth.DBF file, import into DB 
    print("Importing national Gage_Smooth.DBF ...")
    cursor = conn.cursor()
    dbf = subprocess.check_output("%s %s -type f -iname Gage_Smooth.DBF -print" % (pathOfFind, args.outputDir,), shell=True).split()[0]
    assert(dbf)
    print dbf
    f = open(dbf, 'rb')
    db = list(dbfreader(f))
    f.close()
    records = db[2:]
    for record in records:
        #print record
        cursor.execute("""INSERT INTO Gage_Smooth
    (SITE_NO,YEAR,MO,AVE,COMPLETERE)
    VALUES (?,?,?,?,?)""",
        (unicode(record[0], errors='replace'), record[1], record[2], float(record[3]), float(record[4]) ))
    conn.commit()
    cursor.close()
    
    conn.close()