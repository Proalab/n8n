import jwt  # PyJWT library
import time
import json

# Replace with your App Store Connect credentials
APP_STORE_CREDENTIALS = {
    "issuer_id": "29b2d53e-0a54-4357-881c-19a66f92a582",
    "key_id": "S4KKH527VM",
    "private_key": """-----BEGIN PRIVATE KEY-----
MIGTAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBHkwdwIBAQQgoLoF0/zSleIH/ymR
dG9SmrFtUmI0GVVIa/k7tm4KkvSgCgYIKoZIzj0DAQehRANCAAQHFybNU+rBy2uG
A4ysFxPqENXzGBqg/X1MfVxE99iT7FqzOGjysCSTUeGtY0TvsONG7rRSigr3L8of
Isr5iLMv
-----END PRIVATE KEY-----"""
}

def generate_jwt():
    try:
        # JWT payload
        payload = {
            "iss": APP_STORE_CREDENTIALS["issuer_id"],
            "exp": int(time.time()) + 600,  # Expires in 10 minutes
            "aud": "appstoreconnect-v1"
        }

        # Generate JWT token
        token = jwt.encode(
            payload,
            APP_STORE_CREDENTIALS["private_key"],
            algorithm="ES256",
            headers={"kid": APP_STORE_CREDENTIALS["key_id"]}
        )

        return token

    except Exception as e:
        return str(e)

if __name__ == "__main__":
    jwt_token = generate_jwt()
    print(json.dumps({"token": jwt_token}))  # Print JSON output