from django import template
from django.utils.safestring import mark_safe
import re

register = template.Library()

@register.filter
def return_engName(l, i):
    try:
        return l[i].EngName
    except:
        return ""

@register.filter
def return_id(l, i):
    try:
        return l[i].id
    except:
        return ""

@register.filter
def render_mentions(comment_body):
    """
    Transform @mentions in comment text into clickable styled HTML elements
    Supports @"First Last" and @everyone formats
    """
    if not comment_body:
        return comment_body
    
    # Import models to lookup users
    from users.models import CustomUser as Employee
    from django.utils.html import escape
    
    escaped_body = escape(comment_body)
    
    # Use placeholders to protect processed mentions from further processing
    placeholder_counter = 0
    placeholders = {}
    
    # Pattern 1: @"First Last" - names in quotes (process these first)
    quoted_pattern = r'@&quot;([^&]+)&quot;'  # Escaped quotes
    
    def replace_quoted_mention(match):
        nonlocal placeholder_counter
        name = match.group(1).strip()
        
        if name.lower() == 'everyone':
            html = f'<span class="mention mention-everyone">@everyone</span>'
        else:
            # Try to find the user and create profile link
            display_name = name[:30] + '...' if len(name) > 30 else name
            
            # Look up user by name
            name_parts = name.split()
            user_id = None
            if len(name_parts) >= 2:
                first_name = name_parts[0]
                last_name = ' '.join(name_parts[1:])
                try:
                    user = Employee.objects.get(
                        first_name__iexact=first_name,
                        last_name__iexact=last_name,
                        is_active=True
                    )
                    user_id = user.id
                except Employee.DoesNotExist:
                    pass
            
            if user_id:
                html = f'<a href="/profile/{user_id}/" class="mention mention-user" data-user-id="{user_id}">@{escape(display_name)}</a>'
            else:
                html = f'<span class="mention mention-user">@{escape(display_name)}</span>'
        
        # Replace with placeholder
        placeholder = f'__MENTION_PLACEHOLDER_{placeholder_counter}__'
        placeholders[placeholder] = html
        placeholder_counter += 1
        return placeholder
    
    # Apply quoted mentions first, replacing with placeholders
    result = re.sub(quoted_pattern, replace_quoted_mention, escaped_body, flags=re.IGNORECASE)
    
    # Pattern 2: @word - single word mentions (only process @word not in placeholders)
    word_pattern = r'@(\w+)'
    
    def replace_word_mention(match):
        nonlocal placeholder_counter
        word = match.group(1).strip()
        
        if word.lower() == 'everyone':
            html = f'<span class="mention mention-everyone">@everyone</span>'
        else:
            # Try to find user by username or first name
            user_id = None
            try:
                user = Employee.objects.get(username__iexact=word, is_active=True)
                user_id = user.id
            except Employee.DoesNotExist:
                try:
                    user = Employee.objects.get(first_name__iexact=word, is_active=True)
                    user_id = user.id
                except Employee.DoesNotExist:
                    pass
            
            if user_id:
                html = f'<a href="/profile/{user_id}/" class="mention mention-user" data-user-id="{user_id}">@{escape(word)}</a>'
            else:
                html = f'<span class="mention mention-user">@{escape(word)}</span>'
        
        # Replace with placeholder
        placeholder = f'__MENTION_PLACEHOLDER_{placeholder_counter}__'
        placeholders[placeholder] = html
        placeholder_counter += 1
        return placeholder
    
    # Apply word mentions
    result = re.sub(word_pattern, replace_word_mention, result, flags=re.IGNORECASE)
    
    # Replace all placeholders with actual HTML
    for placeholder, html in placeholders.items():
        result = result.replace(placeholder, html)
    
    return mark_safe(result)