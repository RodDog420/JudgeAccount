# Database Management Workflow

## Important Rules
1. NEVER use `db.create_all()` - we use Flask-Migrate
2. NEVER manually edit the database
3. ALWAYS create migrations for model changes

## When You Change Models

### Adding/Removing/Modifying Fields:
```PowerShell
# 1. Edit your models.py file
# 2. Create migration
flask db migrate -m "Describe what you changed"
# 3. Review the migration file in migrations/versions/
# 4. Apply migration
flask db upgrade
```

### If Migration Has Errors:
```PowerShell
# Delete the bad migration file
del migrations\versions\XXXXX_bad_migration.py
# Try again
flask db migrate -m "Description"
```

### Starting Fresh (NUCLEAR OPTION - loses all data):
```PowerShell
del instance\judge_review.db
Remove-Item -Recurse -Force migrations
flask db init
flask db migrate -m "Initial schema"
flask db upgrade
# Recreate admin user (see Step 3 above)
```

## Common Commands

### Check current database version:
```PowerShell
flask db current
```

### View migration history:
```PowerShell
flask db history
```

### Rollback last migration:
```PowerShell
flask db downgrade
```

## Troubleshooting

**Error: "No changes in schema detected"**
- Cause: Database already has tables
- Solution: Delete database, run migration again

**Error: "Constraint must have a name"**
- Cause: Bad migration auto-generation
- Solution: Delete bad migration, regenerate

**Error: "Column already exists"**
- Cause: Mixing db.create_all() with migrations
- Solution: Never use db.create_all() - stick to migrations only
```

### Step 5: Update Your `.gitignore`

Make sure your `.gitignore` includes:
```
instance/
*.db
*.db-journal
__pycache__/
*.pyc
.env