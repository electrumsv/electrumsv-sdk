@echo off
@rem "to specify default python version to 3.9 create/edit ~/AppData/Local/py.ini with [default] set
 to python3=3.9"
set SDKDIR=%~dp0..\electrumsv_sdk
py -3.7 -m pip install pylint
py -3.7 -m pylint --rcfile ../.pylintrc %SDKDIR%
