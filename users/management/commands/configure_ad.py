from django.core.management.base import BaseCommand
from django.conf import settings
import os


class Command(BaseCommand):
    help = 'Configure Active Directory authentication settings'

    def add_arguments(self, parser):
        parser.add_argument(
            '--enable',
            action='store_true',
            help='Enable AD authentication',
        )
        parser.add_argument(
            '--disable',
            action='store_true',
            help='Disable AD authentication',
        )
        parser.add_argument(
            '--server-uri',
            type=str,
            help='LDAP server URI (e.g., ldap://dc.company.com)',
        )
        parser.add_argument(
            '--bind-dn',
            type=str,
            help='Bind DN for LDAP connection',
        )
        parser.add_argument(
            '--bind-password',
            type=str,
            help='Bind password for LDAP connection',
        )
        parser.add_argument(
            '--user-search-base',
            type=str,
            help='Base DN for user searches (e.g., ou=Users,dc=company,dc=com)',
        )

    def handle(self, *args, **options):
        if options['enable']:
            self.enable_ad(options)
        elif options['disable']:
            self.disable_ad()
        else:
            self.show_status()

    def enable_ad(self, options):
        self.stdout.write("Enabling Active Directory authentication...")
        
        # Check if required packages are installed
        try:
            import ldap
            import django_auth_ldap
        except ImportError:
            self.stdout.write(
                self.style.ERROR('django-auth-ldap package is not installed. Run: pip install django-auth-ldap')
            )
            return

        # Check if all required settings are provided
        required_settings = ['server_uri', 'bind_dn', 'bind_password', 'user_search_base']
        missing_settings = [s for s in required_settings if not options.get(s.replace('_', '_'))]
        
        if missing_settings:
            self.stdout.write(
                self.style.ERROR(f'Missing required settings: {", ".join(missing_settings)}')
            )
            self.stdout.write('Example usage:')
            self.stdout.write(
                'python manage.py configure_ad --enable '
                '--server-uri "ldap://your-domain-controller.company.com" '
                '--bind-dn "cn=service-account,ou=Service Accounts,dc=company,dc=com" '
                '--bind-password "your-service-account-password" '
                '--user-search-base "ou=Users,dc=company,dc=com"'
            )
            return

        # Generate settings snippet
        settings_snippet = f'''
# Active Directory Configuration (Auto-generated)
ENABLE_AD_AUTHENTICATION = True
AUTH_LDAP_SERVER_URI = "{options['server_uri']}"
AUTH_LDAP_BIND_DN = "{options['bind_dn']}"
AUTH_LDAP_BIND_PASSWORD = "{options['bind_password']}"

# User search configuration
AUTH_LDAP_USER_SEARCH = LDAPSearch(
    "{options['user_search_base']}",
    ldap.SCOPE_SUBTREE,
    "(sAMAccountName=%(user)s)"
)

# Attribute mapping from AD to Django user model
AUTH_LDAP_USER_ATTR_MAP = {{
    "first_name": "givenName",
    "last_name": "sn",
    "email": "mail",
}}

# Always update user on login
AUTH_LDAP_ALWAYS_UPDATE_USER = True
'''

        self.stdout.write(self.style.SUCCESS('AD authentication configuration:'))
        self.stdout.write(settings_snippet)
        self.stdout.write(
            self.style.WARNING('Add the above configuration to your settings.py file and restart the server.')
        )

    def disable_ad(self):
        self.stdout.write("To disable AD authentication, set ENABLE_AD_AUTHENTICATION = False in settings.py")

    def show_status(self):
        enabled = getattr(settings, 'ENABLE_AD_AUTHENTICATION', False)
        status = "ENABLED" if enabled else "DISABLED"
        style = self.style.SUCCESS if enabled else self.style.WARNING
        
        self.stdout.write(f"Active Directory authentication: {style(status)}")
        
        if enabled:
            server_uri = getattr(settings, 'AUTH_LDAP_SERVER_URI', 'Not configured')
            self.stdout.write(f"Server URI: {server_uri}")
        
        self.stdout.write("\nUse --help to see configuration options.")