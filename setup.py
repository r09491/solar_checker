from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()
    
setup(name='solar_checker',
      version='1.2.0',
      description='Solar checker with APsystems,Anker,Tuya and BrightSky API',
      url='https://github.com/r09491/solar_checker',
      author='r09491',
      author_email='r09491@gmail.com',
      license='MIT',
      long_description=long_description,
      scripts=[
          './scripts/brightsky_latest_get.py',
          './scripts/brightsky_sun_adaptors.py',
          './scripts/apsystems_max_power_set.py',
          './scripts/tuya_plug_latest_get.py',
          './scripts/tuya_plug_switch_set.py',
          './scripts/solar_checker_closest_predict.py',
          './scripts/solar_checker_closest_predict_default.sh',
          './scripts/solar_checker_closest_predict_today.sh',
          './scripts/solar_checker_closest_predict_yesterday.sh',
          './scripts/solar_checker_closest_find_default.sh',
          './scripts/solar_checker_closest_find_today.sh',
          './scripts/solar_checker_closest_find_yesterday.sh',
          './scripts/solar_checker_home_load_set_once.py',
          './scripts/solar_checker_home_load_set_once.sh',
          './scripts/solar_checker_latest_once.py',
          './scripts/solar_checker_latest_once.sh',
          './scripts/solar_checker_switch_once.py',
          './scripts/solar_checker_switch_once_plug2.sh',
          './scripts/solar_checker_switch_on_export_once.py',
          './scripts/solar_checker_switch_on_export_once_plug1.sh',
          './scripts/solar_checker_switch_on_export_once_plug2.sh',
          './scripts/solar_checker_switch_on_export_once_plug3.sh',
          './scripts/solar_checker_switch_on_export_once_plug4.sh',
          './scripts/solar_checker_plot_save.py',
          './scripts/solar_checker_plot_save_today.sh',
          './scripts/solar_checker_plot_save_anyday.sh',
          './scripts/solar_checker_plot_save_yesterday.sh',
          './scripts/solar_checker_slots.py',
          './scripts/solar_checker_slots.sh',
          './scripts/solar_checker_slots_anyday.sh',
          './scripts/solar_checker_slots_yesterday.sh',
          './server/main/p12run',
      ],
      packages=[
          'apsystems',
          'brightsky',
          'poortuya',
          'pooranker',
          'tasmota',
          'utils',
          'utils.plots',
      ],
      install_requires=[
          'aiohttp',
          'aiohttp_jinja2',
          'pyaml',
          'pandas',
          'matplotlib',
          'termgraph',
          'tinytuya',
          'anker_solix_api',
          'ecoflow',
      ],
      zip_safe=False)
