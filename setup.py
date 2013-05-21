from setuptools import setup

def readme():
    with open('README.txt') as f:
        return f.read()

setup(name='ecohydrolib',
      version='0.975',
      description='Libraries and command-line scripts for performing ecohydrology data preparation workflows.',
      long_description=readme(),
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: Unix',
        'Topic :: Scientific/Engineering :: GIS'        
      ],
      url='https://github.com/selimnairb/EcohydrologyWorkflowLib',
      author='Brian Miles',
      author_email='brian_miles@unc.edu',
      license='BSD',
      packages=['ecohydrolib', 'ecohydrolib.tests', 
                'ecohydrolib.nhdplus2', 'ecohydrolib.solim',
                'ecohydrolib.spatialdata', 'ecohydrolib.ssurgo',
                'ecohydrolib.wcs4dem', 'ecohydrolib.climatedata',
                'ecohydrolib.hydro1k'],
      install_requires=[
        'GDAL',
        'pyproj==1.9.2',
        'numpy',
        'lxml',
        'PySimpleSOAP',
        'OWSLib',
        'oset',
        'httplib2'
      ],
      scripts=['bin/NHDPlusV2Setup/NHDPlusV2Setup.py',
               'bin/GHCNDSetup/GHCNDSetup.py',
               'bin/DumpClimateStationInfo.py',
               'bin/DumpMetadataToiRODSXML.py',
               'bin/GenerateSoilPropertyRastersFromSOLIM.py',
               'bin/GenerateSoilPropertyRastersFromSSURGO.py',
               'bin/GetBoundingboxFromStudyareaShapefile.py',
               'bin/GetCatchmentShapefileForHYDRO1kBasins.py',
               'bin/GetCatchmentShapefileForNHDStreamflowGage.py',
               'bin/GetDEMExplorerDEMForBoundingbox.py',
               'bin/GetGHCNDailyClimateDataForBoundingboxCentroid.py',
               'bin/GetGHCNDailyClimateDataForStationsInBoundingbox.py',
               'bin/GetHYDRO1kDEMForBoundingbox.py',
               'bin/GetNHDStreamflowGageIdentifiersAndLocation.py',
               'bin/GetNLCDForDEMExtent.py',
               'bin/GetSSURGOFeaturesForBoundingbox.py'
      ],
      zip_safe=False)
