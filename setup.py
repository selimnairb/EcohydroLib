from setuptools import setup

def readme():
    with open('README.rst') as f:
        return f.read()

setup(name='ecohydrologyworkflowlib',
      version='0.9',
      description='Libraries and command-line scripts for performing ecohydrology data preparation workflows.',
      long_description=readme(),
      classifiers=[
        'Development Status :: 3 - Alpha',
        'Environment :: Console',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: BSD License',
        'Natural Language :: English',
        'Operating System :: Unix',
        'Topic :: Scientific/Engineering :: GIS',
        
      ],
      url='http://...',
      author='Brian Miles',
      author_email='brian_miles@unc.edu',
      license='BSD',
      packages=['ecohydrologyworkflowlib', 'nhdplus2lib', 'solimlib', 'spatialdatalib', 'ssurgolib', 'wcs4demlib'],
      install_requires=[
        'GDAL',
        'pyproj',
        'numpy',
        'lxml',
        'PySimpleSOAP',
        'OWSLib',
        'oset'
      ],
      scripts=['bin/NHDPlusV2Setup/NHDPlusV2Setup',
               'bin/GetBoundingboxFromStudyareaShapefile',
               'bin/GetCatchmentShapefileForStreamflowGage',
               'bin/GetDEMForBoundingbox',
               'bin/GetNHDStreamflowGageIdentifiersAndLocation',
               'bin/GetNLCDForBoundingbox',
               'bin/GetSSURGOFeaturesForBoundingbox'
      ],
      zip_safe=False)
