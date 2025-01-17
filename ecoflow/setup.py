from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()
    
setup(name='ecoflow',
      version='0.0.0',
      description='API for Ecoflow Delta Max',
      url='https://github.com/r09491/solar_checker/ecoflow',
      author='r09491',
      author_email='r09491@gmail.com',
      license='MIT',
      long_description=long_description,
      scripts=[
          './scripts/get_ef_ac_in_out_charge_watts_soc.py',
          './scripts/get_ef_ac_in_out_charge_watts_soc.py',
          './scripts/set_ef_12V_out_enabled.py',
          './scripts/set_ef_ac_charge_watts_balance.py',
          './scripts/set_ef_ac_charge_watts.py',
          './scripts/set_ef_ac_out_enabled.py',
          './scripts/set_ef_beep_muted.py',
          './scripts/set_ef_usb_out_enabled.py',
      ],
      packages=[
          'ecoflow',
      ],
      install_requires=[
          'aiohttp',
      ],
      zip_safe=False)
