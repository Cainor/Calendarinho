import ldap
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.conf import settings
from django_auth_ldap.backend import LDAPBackend
import logging

logger = logging.getLogger(__name__)
User = get_user_model()


class DualAuthenticationBackend(ModelBackend):
    """
    Custom authentication backend that supports both local Django authentication
    and Active Directory (LDAP) authentication.
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
        
        # First try local authentication
        user = self._authenticate_local(username, password)
        if user:
            logger.info(f"Local authentication successful for user: {username}")
            return user
        
        # If local authentication fails and AD is enabled, try AD authentication
        if getattr(settings, 'ENABLE_AD_AUTHENTICATION', False):
            user = self._authenticate_ad(username, password)
            if user:
                logger.info(f"AD authentication successful for user: {username}")
                return user
        
        logger.warning(f"Authentication failed for user: {username}")
        return None
    
    def _authenticate_local(self, username, password):
        """Authenticate against local Django user database"""
        try:
            user = User.objects.get(username__iexact=username)
            if user.check_password(password) and self.user_can_authenticate(user):
                # Ensure auth_source is set for local users
                if user.auth_source != User.LOCAL:
                    user.auth_source = User.LOCAL
                    user.save()
                return user
        except User.DoesNotExist:
            pass
        return None
    
    def _authenticate_ad(self, username, password):
        """Authenticate against Active Directory"""
        if not hasattr(settings, 'AUTH_LDAP_SERVER_URI'):
            logger.error("AD authentication enabled but AUTH_LDAP_SERVER_URI not configured")
            return None
        
        try:
            # Use django-auth-ldap for AD authentication
            ldap_backend = LDAPBackend()
            user = ldap_backend.authenticate(None, username=username, password=password)
            
            if user:
                # Ensure the user has the required fields for our application
                self._sync_user_from_ad(user)
                return user
                
        except Exception as e:
            logger.error(f"AD authentication error for {username}: {str(e)}")
            
        return None
    
    def _sync_user_from_ad(self, user):
        """Sync additional user data from AD to local user model"""
        # Set auth_source to AD
        user.auth_source = User.ACTIVE_DIRECTORY
        
        # Set default user_type if not already set
        if not user.user_type:
            # Default to Employee, can be changed manually by admin
            user.user_type = User.Employee
        
        # Ensure user is active
        if not user.is_active:
            user.is_active = True
            
        user.save()