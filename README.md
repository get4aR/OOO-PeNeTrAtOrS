### AvitOff AD CTF service

#### Description
AvitOff is a bulletin board service where users can post advertisements. It features user profiles, private ads, and JWT-based authentication.

Vulnerabilities:
1. JWT Authentication Bypass: The validation logic in auth.py skips signature verification if the alg header is not in the whitelist (e.g., alg: none), but still processes the sub claim. This allows full Account Takeover.
2. Information Disclosure: The /ads/{ad_id}/contact_info endpoint leaks the seller's email address for any advertisement, regardless of its privacy status. This email is then used to forge the malicious JWT.

Service port: 8000 (default)

---

#### Deployment
The service requires a SECRET_KEY for JWT operations and a PORT environment variable if you want to override the default.

export SECRET_KEY="your_super_secret_key"
export PORT=8000
# Run the application
uvicorn main:app --host 0.0.0.0 --port $PORT
---

#### Checker
The checker uses standard Hackerdom/ForcAD exit codes.

# General availability check
./checker.py check 127.0.0.1

# Place a flag (returns email:password:ad_id)
./checker.py put 127.0.0.1 <seed> <flag> 1

# Retrieve a flag
./checker.py get 127.0.0.1 "user@example.com:pass123:1" <flag> 1*Note: Set the PORT environment variable to use a non-standard port.*
export PORT=31337 && ./checker.py check 127.0.0.1

---

#### Exploit
The exploit leaks the owner's email and forges a JWT to access private advertisements containing the flag.

# Usage: python3 exploit.py <host> <port> <ad_id>
python3 exploit.py 127.0.0.1 8000 1
