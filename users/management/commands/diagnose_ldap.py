from django.core.management.base import BaseCommand
from django.conf import settings
import ldap
import getpass


class Command(BaseCommand):
    help = 'Diagnose LDAP connection and authentication issues. Use --username <username> to test user authentication.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--username',
            type=str,
            help='Test username for LDAP authentication (required for user authentication tests)',
        )

    def handle(self, *args, **options):
        self.stdout.write("LDAP Connection Diagnostics")
        self.stdout.write("=" * 50)
        
        # Get LDAP settings
        server_uri = getattr(settings, 'AUTH_LDAP_SERVER_URI', None)
        bind_dn = getattr(settings, 'AUTH_LDAP_BIND_DN', None)
        bind_password = getattr(settings, 'AUTH_LDAP_BIND_PASSWORD', None)
        
        if not server_uri:
            self.stdout.write(self.style.ERROR("✗ AUTH_LDAP_SERVER_URI not configured"))
            return
        
        self.stdout.write(f"Server URI: {server_uri}")
        self.stdout.write(f"Bind DN: {bind_dn}")
        
        # Test 1: Basic connection
        self.test_basic_connection(server_uri)
        
        # Test 2: Bind with service account
        if bind_dn and bind_password:
            self.test_service_bind(server_uri, bind_dn, bind_password)
        
        # Test 3: Search for user (if username provided)
        if options['username']:
            self.test_user_search(server_uri, bind_dn, bind_password, options['username'])
            
            # Test 4: Direct user bind (get password securely)
            try:
                password = getpass.getpass(f"Enter password for {options['username']} (for direct bind test): ")
                if password:
                    self.test_user_bind(server_uri, options['username'], password)
                else:
                    self.stdout.write(self.style.WARNING("⚠ Skipping direct user bind test (no password provided)"))
            except KeyboardInterrupt:
                self.stdout.write("\n\nDirect user bind test cancelled by user.")
        else:
            self.stdout.write(self.style.WARNING("⚠ No username provided. Skipping user-specific tests."))

    def test_basic_connection(self, server_uri):
        """Test basic LDAP connection"""
        self.stdout.write("\n1. Testing basic LDAP connection...")
        try:
            conn = ldap.initialize(server_uri)
            conn.set_option(ldap.OPT_REFERRALS, 0)
            conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 10)
            
            # Test simple bind (anonymous)
            conn.simple_bind_s()
            self.stdout.write(self.style.SUCCESS("✓ Basic LDAP connection successful"))
            conn.unbind()
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Basic LDAP connection failed: {e}"))
            return False

    def test_service_bind(self, server_uri, bind_dn, bind_password):
        """Test service account binding"""
        self.stdout.write("\n2. Testing service account bind...")
        try:
            conn = ldap.initialize(server_uri)
            conn.set_option(ldap.OPT_REFERRALS, 0)
            conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 10)
            
            conn.simple_bind_s(bind_dn, bind_password)
            self.stdout.write(self.style.SUCCESS("✓ Service account bind successful"))
            conn.unbind()
            return True
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Service account bind failed: {e}"))
            return False

    def test_user_search(self, server_uri, bind_dn, bind_password, username):
        """Test searching for a user"""
        self.stdout.write(f"\n3. Testing user search for: {username}...")
        try:
            conn = ldap.initialize(server_uri)
            conn.set_option(ldap.OPT_REFERRALS, 0)
            conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
            conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 10)
            
            if bind_dn and bind_password:
                conn.simple_bind_s(bind_dn, bind_password)
            else:
                conn.simple_bind_s()
            
            # Search for user
            search_base = "dc=example,dc=com"
            search_filter = f"(uid={username})"  # Try uid instead of sAMAccountName for test server
            
            self.stdout.write(f"Search base: {search_base}")
            self.stdout.write(f"Search filter: {search_filter}")
            
            result = conn.search_s(search_base, ldap.SCOPE_SUBTREE, search_filter)
            
            if result:
                self.stdout.write(self.style.SUCCESS(f"✓ User found: {len(result)} result(s)"))
                for dn, attrs in result:
                    self.stdout.write(f"  DN: {dn}")
                    if 'cn' in attrs:
                        self.stdout.write(f"  CN: {attrs['cn'][0].decode('utf-8')}")
                    if 'mail' in attrs:
                        self.stdout.write(f"  Email: {attrs['mail'][0].decode('utf-8')}")
            else:
                self.stdout.write(self.style.WARNING("⚠ User not found with current search"))
                
                # Try alternative search filters
                alternative_filters = [
                    f"(sAMAccountName={username})",
                    f"(cn={username})",
                    f"(userPrincipalName={username})"
                ]
                
                for alt_filter in alternative_filters:
                    self.stdout.write(f"Trying alternative filter: {alt_filter}")
                    result = conn.search_s(search_base, ldap.SCOPE_SUBTREE, alt_filter)
                    if result:
                        self.stdout.write(self.style.SUCCESS(f"✓ User found with filter: {alt_filter}"))
                        break
            
            conn.unbind()
            return len(result) > 0 if result else False
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ User search failed: {e}"))
            return False

    def test_user_bind(self, server_uri, username, password):
        """Test direct user authentication"""
        self.stdout.write(f"\n4. Testing direct user bind for: {username}...")
        
        # Try different DN formats
        user_dns = [
            f"uid={username},dc=example,dc=com",
            f"cn={username},dc=example,dc=com",
            f"sAMAccountName={username},dc=example,dc=com"
        ]
        
        for user_dn in user_dns:
            try:
                self.stdout.write(f"Trying DN: {user_dn}")
                conn = ldap.initialize(server_uri)
                conn.set_option(ldap.OPT_REFERRALS, 0)
                conn.set_option(ldap.OPT_PROTOCOL_VERSION, 3)
                conn.set_option(ldap.OPT_NETWORK_TIMEOUT, 10)
                
                conn.simple_bind_s(user_dn, password)
                self.stdout.write(self.style.SUCCESS(f"✓ Direct user bind successful with DN: {user_dn}"))
                conn.unbind()
                return True
                
            except Exception as e:
                self.stdout.write(f"  Failed: {e}")
                continue
        
        self.stdout.write(self.style.ERROR("✗ All direct user bind attempts failed"))
        return False