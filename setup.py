import sys
from setuptools import setup, find_packages

if sys.version_info.major != 3:
    print('This Python is only compatible with Python 3, but you are running '
          'Python {}. The installation will likely fail.'.format(sys.version_info.major))

long_description = """
CI Link
Documentation Link
Install inside Simulation/ with `pip3 install -e .`
"""

setup(name='UBC-Solar-Simulation',
      packages=[package for package in find_packages()
                if package.startswith('simulation')],
      package_data={
          'simulation': ['py.typed'],
      },
      install_requires=[
          'numpy', 'bokeh', 'scipy', 'requests', 'polyline', 'tqdm', 'matplotlib', 'pandas', 'seaborn', 'numba',
          'bayesian_optimization', 'timezonefinder', "python-dotenv", 'plotly'
      ],
      extras_require={
          'mpi': [
              'mpi4py',
          ]
      },
      include_package_data=True,
      description='UBC Solar\'s simulation environment',
      author='Fisher Xue',
      url='https://github.com/UBC-Solar/Simulation',
      author_email='software@ubcsolar.com',
      keywords="car",
      license="MIT",
      long_description=long_description,
      long_description_content_type='text/markdown',
      version="0.5.4-alpha"
      )
