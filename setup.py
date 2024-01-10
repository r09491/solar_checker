from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()
    
setup(name='solar_checker',
      version='0.0.1',
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
          './scripts/solar_checker_plot.py',
          './scripts/solar_checker_plot.sh',
          './scripts/solar_checker_plot_yesterday.sh',
          './scripts/solar_checker_slots.py',
          './scripts/solar_checker_slots.sh',
          './scripts/solar_checker_slots_yesterday.sh',
      ],
      packages=[
          'apsystems',
          'tasmota',
      ],
      install_requires=[
          'aiohttp',
          'pandas',
          'matplotlib',
      ],
      zip_safe=False)
