# Here are your Instructions
curl -X POST http://localhost:8001/api/admin/provision-user \
     -H "Content-Type: application/json" \
     -d '{"email": "admin@example.com", "password": "SecurePassword123!", "name": "Admin User"}'
