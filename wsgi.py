# coding: utf-8

import os
import sys

# this_path = os.environ['OPENSHIFT_DATA_DIR']
# sys.path.insert(0, this_path)
# sys.path.insert(0, os.environ['OPENSHIFT_DATA_DIR'])

virtenv = os.environ['OPENSHIFT_PYTHON_DIR'] + '/virtenv/'
virtualenv = os.path.join(virtenv, 'bin/activate_this.py')
try:
    execfile(virtualenv, dict(__file__=virtualenv))
except IOError:
    pass

# os.chdir(this_path)

from viralata.app import create_app
application = create_app(os.environ['OPENSHIFT_DATA_DIR'])
