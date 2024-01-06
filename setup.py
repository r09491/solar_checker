from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()
    
setup(name='solar_checker',
      version='0.0.0',
      description='Solar checker with APsystems and Tasmota API',
      url='https://github.com/r09491/solar_checker',
      author='r09491',
      author_email='r09491@gmail.com',
      license='MIT',
      long_description=long_description,
      scripts=[
          './scripts/tasmota_latest_get.py',
          './scripts/tasmota_latest_get_cron.sh',
          './scripts/apsystems_latest_get.py',
          './scripts/apsystems_latest_get_cron.sh',
          './scripts/apsystems_max_power_set.py',
      ],
      packages=[
          'apsystems',
          'tasmota',
      ],
      install_requires=[
          'aiohttp',
      ],
      zip_safe=False)
