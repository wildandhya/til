# Generate Private & Public Key

## 1. Generate Private Key
```bash
openssl genpkey -algorithm RSA -out private.key -aes256
```
- -algorithm RSA: Specifies the RSA algorithm
- -out private.key : Outputs the private key to the file private.Key
- -aes256: Encrypts the private key with a passphrase

## 2. Generate Public Key
```bash
openssl rsa -in private.key -pubout -out public.key
```
- -in private.key: Uses the private key to generate the public key.
- -pubout: Indicates that this is a public key.
- -out public.key: Outputs the public key to the file public.key.

## Generate an Elliptic Curve (EC) Key Pair
Elliptic curve cryptography for better performance and smaller key sizes

## 1. Generate Private Key
```bash
openssl ecparam -genkey -name prime256v1 -out private.key
```
- -name prime256v1: Specifies the curve type.
- -out private.key: Outputs the private key.

## 2. Generate Public Key
```bash
openssl ec -in private.key -pubout -out public.key
```
- -in private.key: Reads the private key.
- -pubout: Outputs the public key.
- -out public.key: Outputs the public key to the file.
