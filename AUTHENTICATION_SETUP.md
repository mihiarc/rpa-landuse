# Authentication Setup Quick Start

## 🔐 Setting up Authentication

The RPA Landuse Analytics application includes a simple password-based authentication system.

### 1. Configure Authentication

Copy the example secrets file and update with your password:

```bash
# Copy the example file
cp .streamlit/secrets.toml.example .streamlit/secrets.toml

# Generate a password hash for your desired password
python -c "import hashlib; print(hashlib.sha256('your_secure_password'.encode()).hexdigest())"

# Edit .streamlit/secrets.toml and replace 'replace_with_your_sha256_password_hash'
# with the generated hash
```

### 2. Run the Application

```bash
streamlit run landuse_app.py
```

Navigate to the application and log in with your configured password.

### 4. Features

- ✅ **Multi-User**: Allows multiple users to be logged in concurrently 
- ✅ **Automatic Logout**: Sessions expire after 8 hours
- ✅ **Secure Hashing**: SHA-256 password hashing
- ✅ **Easy Configuration**: Simple secrets.toml setup


---

**Security Note**: Never commit the actual `.streamlit/secrets.toml` file to version control. Only the `.streamlit/secrets.toml.example` file should be committed.
