from django.core.management.base import BaseCommand
from django.conf import settings
from django.contrib.auth import authenticate
from users.models import CustomUser
import getpass


class Command(BaseCommand):
    help = 'Test Active Directory authentication setup. Use --test-ad-user --username <username> to test with real AD credentials.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--test-ad-user',
            action='store_true',
            help='Test AD authentication with a real test user',
        )
        parser.add_argument(
            '--username',
            type=str,
            help='Test username for AD authentication (required when using --test-ad-user)',
        )

    def handle(self, *args, **options):
        self.stdout.write("Active Directory Authentication Setup Test")
        self.stdout.write("=" * 50)
        
        tests = [
            self.test_authentication_backend,
            self.test_ad_configuration,
            self.test_user_model,
            self.test_local_authentication
        ]
        
        # Add AD user test if requested
        if options['test_ad_user']:
            # Validate username is provided
            if not options['username']:
                self.stdout.write(self.style.ERROR("✗ Username is required when using --test-ad-user"))
                self.stdout.write("\nExample usage:")
                self.stdout.write("  python manage.py test_ad_setup --test-ad-user --username riemann")
                self.stdout.write("  python manage.py test_ad_setup --test-ad-user --username your-ad-username")
                return
            
            # Get password securely
            try:
                password = getpass.getpass(f"Enter password for {options['username']}: ")
                if not password:
                    self.stdout.write(self.style.ERROR("✗ Password cannot be empty"))
                    return
            except KeyboardInterrupt:
                self.stdout.write("\n\nOperation cancelled by user.")
                return
            
            tests.append(lambda: self.test_ad_authentication(
                options['username'], 
                password
            ))
        
        all_passed = True
        for test in tests:
            if not test():
                all_passed = False
        
        self.stdout.write("\n" + "=" * 50)
        if all_passed:
            self.stdout.write(self.style.SUCCESS("✓ All tests passed! AD authentication setup is ready."))
        else:
            self.stdout.write(self.style.ERROR("✗ Some tests failed. Please review the configuration."))

    def test_authentication_backend(self):
        """Test that the authentication backend is properly configured"""
        self.stdout.write("\nTesting authentication backend configuration...")
        
        auth_backends = getattr(settings, 'AUTHENTICATION_BACKENDS', [])
        custom_backend = 'users.authentication.DualAuthenticationBackend'
        
        if custom_backend in auth_backends:
            self.stdout.write(self.style.SUCCESS("✓ Custom authentication backend is configured"))
        else:
            self.stdout.write(self.style.ERROR("✗ Custom authentication backend is NOT configured"))
            return False
        
        return True

    def test_ad_configuration(self):
        """Test AD configuration"""
        self.stdout.write("\nTesting AD configuration...")
        
        ad_enabled = getattr(settings, 'ENABLE_AD_AUTHENTICATION', False)
        self.stdout.write(f"AD Authentication enabled: {ad_enabled}")
        
        if ad_enabled:
            required_settings = [
                'AUTH_LDAP_SERVER_URI',
                'AUTH_LDAP_BIND_DN', 
                'AUTH_LDAP_BIND_PASSWORD',
                'AUTH_LDAP_USER_SEARCH'
            ]
            
            missing_settings = []
            for setting in required_settings:
                if not hasattr(settings, setting):
                    missing_settings.append(setting)
            
            if missing_settings:
                self.stdout.write(self.style.ERROR(f"✗ Missing AD settings: {', '.join(missing_settings)}"))
                return False
            else:
                self.stdout.write(self.style.SUCCESS("✓ All required AD settings are configured"))
                self.stdout.write(f"Server URI: {settings.AUTH_LDAP_SERVER_URI}")
        else:
            self.stdout.write(self.style.WARNING("ℹ AD authentication is disabled"))
        
        return True

    def test_user_model(self):
        """Test user model has auth_source field"""
        self.stdout.write("\nTesting user model...")
        
        try:
            field = CustomUser._meta.get_field('auth_source')
            self.stdout.write(self.style.SUCCESS("✓ auth_source field exists in CustomUser model"))
            
            choices = [choice[0] for choice in field.choices]
            expected_choices = ['local', 'ad']
            
            if all(choice in choices for choice in expected_choices):
                self.stdout.write(self.style.SUCCESS("✓ auth_source field has correct choices"))
            else:
                self.stdout.write(self.style.ERROR(f"✗ auth_source field choices: {choices}, expected: {expected_choices}"))
                return False
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error with auth_source field: {e}"))
            return False
        
        return True

    def test_local_authentication(self):
        """Test local authentication still works"""
        self.stdout.write("\nTesting local authentication...")
        
        try:
            user = authenticate(username='test_user_that_does_not_exist', password='test_password')
            if user is None:
                self.stdout.write(self.style.SUCCESS("✓ Local authentication handles non-existent users correctly"))
            else:
                self.stdout.write(self.style.ERROR("✗ Local authentication returned unexpected result"))
                return False
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ Error during local authentication test: {e}"))
            return False
        
        return True

    def test_ad_authentication(self, username, password):
        """Test actual AD authentication with provided credentials"""
        self.stdout.write(f"\nTesting AD authentication with user: {username}...")
        
        # Check if AD is enabled
        ad_enabled = getattr(settings, 'ENABLE_AD_AUTHENTICATION', False)
        if not ad_enabled:
            self.stdout.write(self.style.ERROR("✗ AD authentication is disabled. Cannot test AD user."))
            return False
        
        try:
            # Test authentication
            user = authenticate(username=username, password=password)
            
            if user:
                self.stdout.write(self.style.SUCCESS(f"✓ AD authentication successful for user: {username}"))
                self.stdout.write(f"  - User ID: {user.id}")
                self.stdout.write(f"  - Full name: {user.get_full_name()}")
                self.stdout.write(f"  - Email: {user.email}")
                self.stdout.write(f"  - Auth source: {user.auth_source}")
                self.stdout.write(f"  - User type: {user.get_user_type_display()}")
                self.stdout.write(f"  - Is active: {user.is_active}")
                
                # Verify auth_source is set correctly
                if user.auth_source == CustomUser.ACTIVE_DIRECTORY:
                    self.stdout.write(self.style.SUCCESS("✓ Auth source correctly set to Active Directory"))
                else:
                    self.stdout.write(self.style.WARNING(f"⚠ Auth source is: {user.auth_source} (expected: {CustomUser.ACTIVE_DIRECTORY})"))
                
                # Check group-based flags if configured
                flags_config = getattr(settings, 'AUTH_LDAP_USER_FLAGS_BY_GROUP', {})
                if flags_config:
                    self.stdout.write("\n  Group-based flags:")
                    for flag in ['is_active', 'is_staff', 'is_superuser']:
                        if flag in flags_config:
                            flag_value = getattr(user, flag, False)
                            self.stdout.write(f"    {flag}: {flag_value} (configured via group: {flags_config[flag]})")
                        else:
                            flag_value = getattr(user, flag, False)
                            self.stdout.write(f"    {flag}: {flag_value} (not configured via groups)")
                else:
                    self.stdout.write(self.style.WARNING("  ⚠ No group-based flags configured"))
                
                return True
            else:
                self.stdout.write(self.style.ERROR(f"✗ AD authentication failed for user: {username}"))
                self.stdout.write("  Possible reasons:")
                self.stdout.write("  - Invalid credentials")
                self.stdout.write("  - LDAP server configuration issues")
                self.stdout.write("  - Network connectivity problems")
                self.stdout.write("  - User search base configuration incorrect")
                return False
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"✗ AD authentication error: {str(e)}"))
            return False