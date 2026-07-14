"""Whitelist for vulture false positives.

Unused parameters on placeholder Celery task implementations in
app/tasks/notifications.py - part of their public task signatures.
"""


class _Whitelist:
    html_body = None
    sender = None
    admin_only = None


_ = _Whitelist()
_.html_body
_.sender
_.admin_only
