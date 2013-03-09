from setuptools import setup

def readme():
    with open('README.txt') as f:
        return f.read()

setup(name='ecohydroworkflowlib',
      version='0.96',
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
      packages=['ecohydroworkflowlib', 'ecohydroworkflowlib.tests', 
                'ecohydroworkflowlib.nhdplus2', 'ecohydroworkflowlib.solim',
                'ecohydroworkflowlib.spatialdata', 'ecohydroworkflowlib.ssurgo',
                'ecohydroworkflowlib.wcs4dem', 'ecohydroworkflowlib.climatedata',
                'ecohydroworkflowlib.hydro1k'],
      install_requires=[
        'GDAL',
        'pyproj==1.9.2',
        'numpy',
        'lxml',
        'PySimpleSOAP',
        'OWSLib',
        'oset',
        'pyspatialite==3.0.1',
        'httplib2'
      ],
      scripts=['bin/NHDPlusV2Setup/NHDPlusV2Setup.py',
               'bin/GHCNDSetup/GHCNDSetup.py',
               'bin/GenerateSoilPropertyRastersFromSSURGO.py',
               'bin/GenerateSoilPropertyRastersFromSOLIM.py',
               'bin/GetBoundingboxFromStudyareaShapefile.py',
               'bin/GetCatchmentShapefileForHYDRO1kBasins.py',
               'bin/GetCatchmentShapefileForStreamflowGage.py',
               'bin/GetDEMExplorerDEMForBoundingbox.py',
               'bin/GetGHCNDailyClimateDataForBoundingboxCentroid.py',
               'bin/GetGHCNDailyClimateDataForStationsInBoundingbox.py',
               'bin/GetHYDRO1kDEMForBoundingbox.py',
               'bin/GetNHDStreamflowGageIdentifiersAndLocation.py',
               'bin/GetNLCDForBoundingbox.py',
               'bin/GetSSURGOFeaturesForBoundingbox.py'
      ],
      zip_safe=False)
