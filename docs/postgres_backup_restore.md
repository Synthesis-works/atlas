# PostgreSQL Backup and Restore Strategy

This document outlines the backup and restore procedures for the Atlas PostgreSQL database.

## 1. Automated Backups (Production)
In a production environment (e.g., AWS RDS or Google Cloud SQL), point-in-time recovery (PITR) and automated daily snapshots must be enabled. 
- **Retention**: Minimum 30 days.
- **RPO (Recovery Point Objective)**: 5 minutes (via WAL archiving).
- **RTO (Recovery Time Objective)**: < 1 hour.

## 2. Manual Backup (pg_dump)
For manual snapshots, migrations, or local environment seeding, use `pg_dump`.

### Creating a Backup
To create a compressed, custom-format backup (recommended for restore flexibility):

```bash
pg_dump -U postgres -h localhost -d atlas -F c -f atlas_backup.dump
```

To create a plain-text SQL script backup:

```bash
pg_dump -U postgres -h localhost -d atlas -F p -f atlas_backup.sql
```

## 3. Manual Restore (pg_restore)
To restore a custom-format backup into a fresh database:

```bash
# First, ensure the target database exists
createdb -U postgres -h localhost atlas_new

# Restore the dump
pg_restore -U postgres -h localhost -d atlas_new -1 atlas_backup.dump
```
*(The `-1` flag ensures the entire restore happens in a single transaction, rolling back on failure).*

## 4. Restoring from a SQL Script
If the backup was created as a plain SQL script (`-F p`):

```bash
psql -U postgres -h localhost -d atlas_new < atlas_backup.sql
```

## 5. Security and Compliance
- **Encryption**: All backups (at rest and in transit) must be encrypted.
- **Access Control**: Backup files must only be accessible to authorized infrastructure personnel (e.g., via IAM roles for S3 buckets).
- **Sanitization**: If restoring a production backup to a staging or local environment, sensitive fields (e.g., PII in `users` table) must be obfuscated or scrubbed.
