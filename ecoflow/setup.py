from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()
    
setup(name='ecoflow',
      version='0.0.2',
      description='API for Ecoflow Delta Max',
      url='https://github.com/r09491/solar_checker/ecoflow',
      author='r09491',
      author_email='r09491@gmail.com',
      license='MIT',
      long_description=long_description,
      scripts=[
          './scripts/ef_12V_out_enabled_set.py',
          './scripts/ef_ac_in_out_charge_watts_soc_get.py',
          './scripts/ef_ac_charge_watts_balance_set.py',
          './scripts/ef_ac_charge_watts_set.py',
          './scripts/ef_ac_out_enabled_set.py',
          './scripts/ef_beep_muted_set.py',
          './scripts/ef_usb_out_enabled_set.py',
          './scripts/ef_sum_watts_get.py',
          './scripts/ef_12V_watts_get.py',
          './scripts/ef_usb_watts_get.py',
          './scripts/ef_ac_watts_get.py',
          './scripts/ef_watts_get.py',
          './scripts/ef_checker_latest_once.py',
          './scripts/ef_checker_latest_once.sh',
      ],
      packages=[
          'ecoflow',
      ],
      install_requires=[
          'aiohttp',
      ],
      zip_safe=False)
