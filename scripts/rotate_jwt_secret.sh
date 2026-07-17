#!/usr/bin/env bash
# rotate_jwt_secret.sh â generate a new JWT_SECRET and print instructions
# Usage: bash scripts/rotate_jwt_secret.sh
set -euo pipefail

NEW_SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(48))")

echo "====================================="
echo " JWT Secret Rotation"
echo "====================================="
echo ""
echo "New JWT_SECRET:"
echo "  JWT_SECRET=$NEW_SECRET"
echo ""
echo "Steps:"
echo "  1. Update JWT_SECRET in your .env / secrets manager"
echo "  2. Restart API: docker compose -f docker-compose.prod.yml restart api worker"
echo "  3. All existing access tokens will immediately be invalidated"
echo "  4. Refresh tokens in DB are still valid â users re-login automatically"
echo ""
echo "For FIELD_ENCRYPTION_KEY rotation, use: python -c \"from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())\""
echo "Note: rotating FIELD_ENCRYPTION_KEY requires a data migration to re-encrypt existing records."
