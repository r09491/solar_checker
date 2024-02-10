from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()
    
setup(name='solar_checker',
      version='0.2.0',
      description='Solar checker with APsystems,Tasmota an Tuya API',
      url='https://github.com/r09491/solar_checker',
      author='r09491',
      author_email='r09491@gmail.com',
      license='MIT',
      long_description=long_description,
      scripts=[
          './scripts/apsystems_max_power_set.py',
          './scripts/tuya_plug_latest_get.py',
          './scripts/tuya_plug_switch_set.py',
          './scripts/solar_checker_latest_once.py',
          './scripts/solar_checker_latest_once.sh',
          './scripts/solar_checker_switch_once.py',
          './scripts/solar_checker_switch_once_balkon.sh',
          './scripts/solar_checker_switch_once_ecoflow.sh',
          './scripts/solar_checker_plot.py',
          './scripts/solar_checker_plot.sh',
          './scripts/solar_checker_plot_anyday.sh',
          './scripts/solar_checker_plot_yesterday.sh',
          './scripts/solar_checker_slots.py',
          './scripts/solar_checker_slots.sh',
          './scripts/solar_checker_slots_anyday.sh',
          './scripts/solar_checker_slots_yesterday.sh',
          './server/main/p12run',
      ],
      packages=[
          'apsystems',
          'tasmota',
          'poortuya',
          'utils',
      ],
      install_requires=[
          'aiohttp',
          'aiohttp_jinja2',
          'pyaml',
          'pandas',
          'matplotlib',
          'termgraph',
          'tinytuya',
      ],
      zip_safe=False)
