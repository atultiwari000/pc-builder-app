from django.apps import AppConfig


def _connect_post_migrate_seed(app_config: AppConfig):
    # Lazy import to avoid early settings/db initialization
    """
    Connects a post-migrate signal handler to seed sample data into the database after migrations for the pcbuilder app.
    
    This function sets up a signal handler that, upon completion of migrations for the pcbuilder app, checks for the presence of specific SQL files at the repository root. If the `vendors` table does not exist, it attempts to create the schema using `database_schema.sql`. It optionally loads compatibility functions from `compatibility_functions.sql`. If the `vendors` table is empty, it seeds sample data from `sample_data.sql`. All operations are performed safely, with errors silently ignored to avoid interfering with the migration process.
    """
    from django.conf import settings
    from django.db import connection, transaction
    from django.db.models.signals import post_migrate
    from pathlib import Path

    sql_path = Path(getattr(settings, 'BASE_DIR'))
    # settings.BASE_DIR points to backend/ per this project; SQL files sit at repo root
    repo_root = sql_path.parent
    # Use default filenames
    schema_sql_file = repo_root / 'database_schema.sql'
    sample_sql_file = repo_root / 'sample_data.sql'
    compat_sql_file = repo_root / 'compatibility_functions.sql'

    def seed_sample_data(sender, app_config=None, **kwargs):
        # Only run when pcbuilder app finishes migrating
        """
        Seeds the database with sample data after migrations for the 'pcbuilder' app.
        
        This function is intended to be used as a Django post-migrate signal handler. It checks for the presence of required SQL files and the existence of the 'vendors' table, creates the schema if necessary, loads compatibility functions if available, and populates the database with sample data if it has not already been seeded. All operations are performed safely to avoid interrupting the migration process.
        """
        if app_config and app_config.name != 'pcbuilder':
            return
        # Abort if sample file is missing
        if not sample_sql_file.exists():
            return
        try:
            with connection.cursor() as cursor:
                # Ensure schema exists; if vendors table is missing, try to create schema first
                cursor.execute(
                    """
                    SELECT COUNT(*)
                    FROM information_schema.tables
                    WHERE table_schema = 'public' AND table_name = 'vendors'
                    """
                )
                vendors_table_exists = bool(cursor.fetchone()[0])

            if not vendors_table_exists and schema_sql_file.exists():
                try:
                    schema_sql_text = schema_sql_file.read_text(encoding='utf-8')
                    if schema_sql_text.strip():
                        with transaction.atomic():
                            with connection.cursor() as cursor:
                                cursor.execute(schema_sql_text)
                except Exception:
                    # If schema creation fails, skip seeding silently
                    return

            # Optionally load compatibility functions (safe if already present)
            if compat_sql_file.exists():
                try:
                    compat_sql_text = compat_sql_file.read_text(encoding='utf-8')
                    if compat_sql_text.strip():
                        with transaction.atomic():
                            with connection.cursor() as cursor:
                                cursor.execute(compat_sql_text)
                except Exception:
                    pass

            # If vendors already has rows, assume seeded and skip
            with connection.cursor() as cursor:
                try:
                    cursor.execute('SELECT COUNT(*) FROM vendors;')
                    count = cursor.fetchone()[0]
                    if count and int(count) > 0:
                        return
                except Exception:
                    return

            # Load and execute the SQL in a transaction
            sql_text = sample_sql_file.read_text(encoding='utf-8')
            if not sql_text.strip():
                return
            with transaction.atomic():
                with connection.cursor() as cursor:
                    cursor.execute(sql_text)
        except Exception:
            # Swallow errors to avoid breaking migrations; admin can load manually if needed
            return

    # Connect once
    post_migrate.connect(seed_sample_data, dispatch_uid='pcbuilder_seed_sample_data')


class PcbuilderConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pcbuilder'

    def ready(self):
        """
        Initializes the post-migration data seeding process when the app is ready.
        """
        _connect_post_migrate_seed(self)
