# -*- coding: utf-8 -*-
"""
Created on Tue Sep 12 2023

@author: Wei Xiong
"""
import PyInstaller.__main__
import shutil
import os
from pathlib import Path
ROOT_DIR = Path(__file__).parent.parent
GUI_SETTINGS_DIR = ROOT_DIR.joinpath('gui_settings')
TOSA_BAY_MAP = GUI_SETTINGS_DIR.joinpath('tosa_bay.yaml')
print(TOSA_BAY_MAP)
DIR = 'dist'
# remove dist folder
if os.path.exists(DIR):
    shutil.rmtree(DIR)

# # build the exe
# PyInstaller.__main__.run([       
#     '--onefile',
#     '--windowed',
#     '--clean',
#     '-n BI',
#     rf'--distpath={DIR}',
#     # r'--hidden-import=openpyxl.cell._writer',
#     # '--paths DIR1 : DIR2',
#     # r'--add-data=resources\EP_logo.png;resources',
#     # r'--add-data=resources\exfo_BA_API_X64.dll;resources',
#     # r'--add-data=resources\exfo_EA_API_Int_X64.dll;resources',
#     # r'--add-data=resources\multilane_4024.dll;resources',
#     # r'--add-data=resources\multilane_4041.dll;resources',
#     # r'--add-data=config\instr_cfg.yml;config',
#     # r'--add-data=config\mcb_cfg.yml;config',
#     # r'--add-data=config\test_cfg.yml;config',
#     # r'--add-data=config\spec\spec_sfp28.yml;config\spec',    
#     # r'--add-data=config\spec\spec_sfpp.yml;config\spec',   
#     # r'--add-data=config\spec\spec_sfpp_Finisar.yml;config\spec',   
#     # r'--add-data=data\cal_data\fts_cal.csv;data\cal_data',   
#     'main.py'
# ])

PyInstaller.__main__.run([       
    '--onefile',
    # '--windowed',
    '--clean',
    '-npl_cal',
    rf'--distpath={DIR}',
    # r'--hidden-import=openpyxl.cell._writer',
    # '--paths DIR1 : DIR2',
    # r'--add-data=resources\EP_logo.png;resources',
    # r'--add-data=resources\exfo_BA_API_X64.dll;resources',
    # r'--add-data=resources\exfo_EA_API_Int_X64.dll;resources',
    # r'--add-data=resources\multilane_4024.dll;resources',
    # r'--add-data=resources\multilane_4041.dll;resources',
    # r'--add-data=config\instr_cfg.yml;config',
    # r'--add-data=config\mcb_cfg.yml;config',
    # r'--add-data=config\gui_settings\tosa_bay.yaml;gui_settings',
    # r'--add-data=config\test_cfg.yml;config',
    # r'--add-data=config\spec\spec_sfp28.yml;config\spec',    
    # r'--add-data=config\spec\spec_sfpp.yml;config\spec',   
    # r'--add-data=config\spec\spec_sfpp_Finisar.yml;config\spec',   
    # r'--add-data=data\cal_data\fts_cal.csv;data\cal_data',   
    'gui_cal.py'
])

# copy the resources files into dist
shutil.copytree(r'gui_settings', rf'{DIR}\gui_settings')
shutil.copytree(r'image', rf'{DIR}\image')
# shutil.copytree(r'data\cal_data',rf'{DIR}\data\cal_data')
