# Generate Random Password

## Command
```bash
openssl rand -base64 12
```
- rand: Generates random data.
- -base64: Encodes the output in Base64 format, making it human-readable.
- 12: Specifies the number of random bytes. Since Base64 encoding increases size, the output password will be approximately 16 characters long.
