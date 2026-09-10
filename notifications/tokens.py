"""
Signed tokens carried in email links.

A link in an email has no session behind it, so the link itself has to say
who it was sent to and what it is for, in a way nobody can forge or edit.
Django's signing does exactly that: the payload is HMAC-signed with the
site's SECRET_KEY and timestamped, so a token that was tampered with, made
up, or is simply too old is refused before anything looks at its contents.

The move-request token names the request and the recipient. It does not
name the action — the same link opens a confirmation page where the admin
chooses, and confirms, approve or reject. That page exists because mail
scanners follow links: a link that acted on GET would let an antivirus
proxy approve a child's move by prefetching it.
"""

from django.core import signing

# Salted so a token minted for one purpose can never be replayed as another.
MOVE_ACTION_SALT = 'children.move-request.email-action'

# Two weeks. Long enough to cover a holiday; short enough that a link found
# in an old mailbox is dead.
MOVE_ACTION_MAX_AGE = 14 * 24 * 60 * 60


def make_move_action_token(move_request_id, email):
    """A URL-safe token binding this move request to this recipient."""
    return signing.dumps(
        {
            'move_request_id': str(move_request_id),
            'email': (email or '').strip().lower(),
        },
        salt=MOVE_ACTION_SALT,
    )


def read_move_action_token(token):
    """
    The payload of a token this site issued.

    Raises signing.SignatureExpired once it is older than MOVE_ACTION_MAX_AGE,
    and signing.BadSignature (its parent) for anything forged or altered.
    """
    payload = signing.loads(token, salt=MOVE_ACTION_SALT, max_age=MOVE_ACTION_MAX_AGE)
    if not isinstance(payload, dict) or not payload.get('move_request_id') \
            or not payload.get('email'):
        raise signing.BadSignature('Token payload is not a move action.')
    return payload
