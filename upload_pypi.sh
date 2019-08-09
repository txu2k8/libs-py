#!/bin/bash                                                                                                                                                                                                   
# ##########################################################################                           
# Author: txu
# Brief:  Upload tlib to pypi
#                                                                                                      
# Returns:                                                                                             
#   pass: 0
#   fail: not 0                                                                                        
# ##########################################################################   
rm -rf ./build ./tlib.egg-info ./dist
python setup.py sdist bdist_wheel
twine upload  dist/*
