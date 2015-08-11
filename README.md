# Vira-Lata (EXPERIMETAL!!!)

Microservice for Authentication: Restlike & Social.

Similar to [microauth](https://github.com/LukeB42/microauth), but merged with [python-social-auth](https://github.com/omab/python-social-auth) to allow auth using other providers.
Instead of Microauth, Vira-Lata has no role management.

The protocol is similar to [Kerberos](https://en.wikipedia.org/wiki/Kerberos_%28protocol%29), having "main" and "micro" tokens.


**This code should not yet be used in production!**


## Install

python setup.py install

## Prepare BD

python manage.py initdb

## Run!

python manage.py run
