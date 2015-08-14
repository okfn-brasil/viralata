#!/usr/bin/env python
# coding: utf-8


def decode_validate_token(token, sv, api):
    """This tries to be a general function to decode and validade any token.
    Receives a token, a SignerVerifier and an API.
    """
    try:
        decoded = sv.decode(token)
        # options={"verify_exp": False})
    except sv.ExpiredSignatureError:
        api.abort(400, "Error: Expired token!")
    except:
        # TODO: tratar erros... quais são?
        raise

    # Verify if token has all fields
    for fields in ['username', 'type', 'exp']:
        if fields not in decoded.keys():
            api.abort(400, "Error: Malformed token! No: %s" % fields)

    return decoded


def decode_token(token, sv, api):
    """This function tries to decode and valitade a token used by a client micro
    service. A client micro service is anyone without knowlegde of revoked main
    tokens. Because of this, they should only accept micro tokens."""
    decoded = decode_validate_token(token, sv, api)
    if decoded['type'] != 'micro':
        api.abort(400, "Error: This is not a micro token!")
    return decoded
