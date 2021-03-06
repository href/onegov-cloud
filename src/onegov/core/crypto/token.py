import hashlib
import secrets

from pathlib import Path


# for external reference, update if the hashing function ever changes
RANDOM_TOKEN_LENGTH = 64


def random_token(nbytes=512):
    """ Generates an unguessable token. Generates a random string with
    the given number of bytes (may not be lower than 512) and hashes
    the result to get a token with a consistent length of 64.

    Why hashing?

    We could of course just create a random token with a length of 64, but that
    would leak the random numbers we actually create. This can be a bit of
    a problem if the random generator you use turns out to have some
    vulnerability. By hashing a larger number we hide the result of our random
    generator.

    Doesn't generating a hash from a larger number limit the number of tokens?

    Yes it does. The number of different tokens is 2^256 after hashing,
    which is a number larger than all the atoms on earth (approx. 2^166).
    So there is a chance of a collision occuring, but it is *very* unlikely
    to *ever* happen.

    More information:

    `<http://wyattbaldwin.com/2014/01/09/generating-random-tokens-in-python>`_

    `<http://www.2uo.de/myths-about-urandom/>`_

    `<http://crypto.stackexchange.com/q/1401>`_

    """
    assert nbytes >= 512
    return hashlib.sha256(secrets.token_bytes(nbytes)).hexdigest()


def stored_random_token(namespace, name):
    """ A random token that is only created once per boot of the host
    (assuming the host deletes all files in the /tmp folder).

    This method should only be used for development and is not meant for
    general use!

    """
    container = Path('/tmp/onegov-secrets')
    container.mkdir(mode=0o700, exist_ok=True)

    namespace = container / namespace
    namespace.mkdir(mode=0o700, exist_ok=True)

    path = container / namespace / name

    if path.exists():
        with path.open('r') as f:
            return f.read()

    token = random_token()

    with path.open('w') as f:
        f.write(token)

    path.chmod(0o400)

    return token
