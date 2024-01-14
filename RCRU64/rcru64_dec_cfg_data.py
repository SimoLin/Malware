# MIT License
#
# Copyright (c) 2023-2024 Andrey Zhdanov (rivitna)
# https://github.com/rivitna
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and associated documentation files
# (the "Software"), to deal in the Software without restriction, including
# without limitation the rights to use, copy, modify, merge, publish,
# distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to
# the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
# FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER
# DEALINGS IN THE SOFTWARE.

import sys
import io
import os
import base64
from Crypto.Cipher import AES


# Well-known end markers of encryption stage 1
END_MARKERS1 = [
    b'AppData',
    b'Studio',
    b'tasklist',
    b'Registery',
    b'Version',
    b'Windows',
    b'Library'
]

# End marker of encryption stage 2
END_MARKER2 = b'U12H6AN=='

KEY_LEN = 32
NONCE_LEN = 12
MAC_TAG_SIZE = 16


def decode_and_decrypt(enc_data: bytes, key: bytes, nonce: bytes) -> bytes:
    """Decode and decrypt data"""

    enc_data = base64.b64decode(enc_data)

    cipher = AES.new(key, AES.MODE_GCM, nonce)

    tag = enc_data[-MAC_TAG_SIZE:]

    try:
        enc_data = cipher.decrypt_and_verify(enc_data[:-MAC_TAG_SIZE], tag)
    except ValueError:
        return None

    return base64.b64decode(enc_data)


def decrypt_data(enc_data: bytes, key: bytes, nonces: bytes) -> bytes:
    """Decrypt data"""

    # Decode and decrypt data (encryption stage 2)
    enc_data = decode_and_decrypt(enc_data, key, nonces[NONCE_LEN:])
    if enc_data is None:
        return None

    # Find end marker
    i = enc_data.find(END_MARKER2)
    if i < 0:
        return None
    enc_data = enc_data[:i]

    # Remove dublicate encrypted data
    if i & 1 == 0:
        i >>= 1
        if enc_data[i:] == enc_data[:i]:
            enc_data = enc_data[i:]

    # Decode and decrypt data (encryption stage 1)
    data = decode_and_decrypt(enc_data, key, nonces[:NONCE_LEN])

    # Find end marker
    for end_marker in END_MARKERS1:
        i = data.find(end_marker)
        if i >= 0:
            return data[:i]

    return data


#
# Main
#
if len(sys.argv) != 2:
    print('Usage:', os.path.basename(sys.argv[0]), 'filename')
    sys.exit(0)

with io.open('./cfg_key.bin', 'rb') as f:
    key = f.read(KEY_LEN)

with io.open('./cfg_nonces.bin', 'rb') as f:
    nonces = f.read(2 * NONCE_LEN)

filename = sys.argv[1]
with io.open(filename, 'rb') as f:
    enc_data = f.read()

data = decrypt_data(enc_data, key, nonces)
if data is None:
    print('Error: Failed to decrypt cfg data')
    sys.exit(1)

new_filename = filename + '.dec'
with io.open(new_filename, 'wb') as f:
    f.write(data)

print('Done!')
