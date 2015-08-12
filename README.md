# Vira-Lata (EXPERIMETAL!!!)

Microservice for Authentication: Restlike & Social.

Similar to [microauth](https://github.com/LukeB42/microauth), but built over [python-social-auth](https://github.com/omab/python-social-auth) to allow auth using other providers (like oAuth).
Instead of Microauth, Vira-Lata has no role management.

The protocol is similar to [Kerberos](https://en.wikipedia.org/wiki/Kerberos_%28protocol%29), having "main" and "micro" tokens.

An example of web interface using this microservice as backend is [Cuidando2](https://gitlab.com/ok-br/cuidando2).
An exemple of microservice that uses the tokens produced by this microservice is [Tagarela](https://gitlab.com/ok-br/tagarela).


**This code should not yet be used in production!**


## Install

python setup.py install

## Prepare BD

python manage.py initdb

## Run!

python manage.py run


## Name

Vira-Lata, in brazilian portuguese, means mutt/mongrel.
So this name can be considered a more humble version of the mighty [Cerberus](https://en.wikipedia.org/wiki/Cerberus), symbol of the [Kerberos protocol](https://en.wikipedia.org/wiki/Kerberos_%28protocol%29)
