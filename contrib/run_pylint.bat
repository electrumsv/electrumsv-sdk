@echo off
@rem "to specify default python version to 3.9 create/edit ~/AppData/Local/py.ini with [default] set
@rem to python3=3.9"
set SDKDIR=%~dp0..
py -m pip install pylint -U
pushd %SDKDIR%
py -m pylint --rcfile .pylintrc electrumsv_sdk
popd