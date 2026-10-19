"""Regenerate the genuine crypto values shown in the reel (assets/data/crypto.json).
bcrypt salts are random, so a re-run gives a different (equally valid) hash; the committed one verifies against "hunter2"."""
import json, bcrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
h = bcrypt.hashpw(b"hunter2", bcrypt.gensalt(rounds=12)).decode()
key, nonce = bytes(range(32)), bytes.fromhex("cafebabefacedbaddecaf888")  # demo key/nonce, never reuse in production
pt = b"SELECT id, email FROM users WHERE id = 42;"
ct = AESGCM(key).encrypt(nonce, pt, None)
json.dump({"bcrypt": h, "bcrypt_salt": h[7:29], "aes_key_hex": key.hex(), "nonce_hex": nonce.hex(), "plaintext": pt.decode(), "ciphertext_hex": ct.hex()}, open("assets/data/crypto.json", "w"), indent=1)
