"""
Dashboard / Info endpoint — aggregate statistics across all centres.
Matches the /admin/info page on the frontend.
"""
from datetime import date as date_type

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.services import centres_db, sessions_db, children_db, roles_db


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def info_dashboard(request):
    """A snapshot across all centres — children, teachers, sessions, roles and capacity."""
    centres = centres_db.list_centres()
    all_children = children_db.list_children()
    total_centres = len(centres)
    total_children = len(all_children)

    # Aggregate data
    total_rooms = sum(len(c.get('rooms', [])) for c in centres)
    total_sessions = 0
    total_enrolments = 0  # TODO: Needs enrolments table scan or dedicated counter — not yet implemented in Dynamo
    total_roles = 0
    total_people = set()
    total_teachers = set()

    children_per_centre = []
    per_centre_roles = []
    centres_glance = []
    session_popularity = []
    # Build roles_people in a single pass (avoid duplicate list_roles calls)
    roles_people_map = {}

    # PERF: This loop does 3 DDB queries per centre (sessions, slots, roles).
    # For large orgs consider caching (data changes slowly — even 60s TTL helps).
    for centre in centres:
        cid = centre['id']
        sessions = sessions_db.list_sessions(cid)
        total_sessions += len(sessions)
        slots = sessions_db.list_slots(cid)
        roles = roles_db.list_roles(cid)
        total_roles += len(roles)

        # Count children at this centre
        centre_children = [c for c in all_children if c.get('centre_id') == cid]
        children_count = len(centre_children)

        # Count enrolments from children assigned to sessions at this centre
        for child in centre_children:
            if child.get('session_id'):
                total_enrolments += 1

        # Count teachers and people — use a per-centre set to avoid double-counting
        centre_people = set()
        centre_teachers = set()
        for role in roles:
            role_name = role.get('name', '')
            for member in role.get('members', []):
                uid = member.get('user_id')
                if uid:
                    centre_people.add(uid)
                    total_people.add(uid)
                    if 'teacher' in role_name.lower():
                        centre_teachers.add(uid)
                        total_teachers.add(uid)

            # Build roles_people breakdown in the same loop
            name = role_name or 'Unknown'
            member_count = len(role.get('members', []))
            if name not in roles_people_map:
                roles_people_map[name] = 0
            roles_people_map[name] += member_count

        children_per_centre.append({
            'centre_id': cid,
            'centre_name': centre.get('name', ''),
            'children': children_count,
            'teachers': len(centre_teachers),
        })

        per_centre_roles.append({
            'centre_id': cid,
            'centre_name': centre.get('name', ''),
            'people': len(centre_people),
            'roles': len(roles),
        })

        centres_glance.append({
            'centre_id': cid,
            'centre_name': centre.get('name', ''),
            'rooms': len(centre.get('rooms', [])),
            'sessions': len(sessions),
            'slots': len(slots),
            'children': children_count,
            'roles': len(roles),
            'people': len(centre_people),
            'status': 'Active' if slots else 'No schedule',
        })

        # Session popularity: count children whose session_id matches
        for session in sessions:
            session_children = [c for c in centre_children if c.get('session_id') == session['id']]
            session_popularity.append({
                'session_id': session['id'],
                'session_name': session.get('name', ''),
                'enrolments': len(session_children),
            })

    session_popularity.sort(key=lambda x: x['enrolments'], reverse=True)

    # Age distribution
    today = date_type.today()
    age_buckets = {'0-1y': 0, '1-2y': 0, '2-3y': 0, '3-4y': 0, '4-5y': 0, '5y+': 0}
    for child in all_children:
        dob_str = child.get('date_of_birth', '')
        if not dob_str:
            continue
        try:
            dob = date_type.fromisoformat(dob_str)
            age_years = (today - dob).days / 365.25
            if age_years < 1:
                age_buckets['0-1y'] += 1
            elif age_years < 2:
                age_buckets['1-2y'] += 1
            elif age_years < 3:
                age_buckets['2-3y'] += 1
            elif age_years < 4:
                age_buckets['3-4y'] += 1
            elif age_years < 5:
                age_buckets['4-5y'] += 1
            else:
                age_buckets['5y+'] += 1
        except (ValueError, TypeError):
            pass

    roles_people_list = [{'role': k, 'people': v} for k, v in roles_people_map.items()]

    return Response({
        'summary': {
            'centres': total_centres,
            'children': total_children,
            'teachers': len(total_teachers),
            'sessions': total_sessions,
            'rooms': total_rooms,
            'enrolments': total_enrolments,
            'roles': total_roles,
            'people': len(total_people),
        },
        'children_per_centre': children_per_centre,
        'roles_people': roles_people_list,
        'per_centre_roles': per_centre_roles,
        'session_popularity': session_popularity,
        'age_distribution': age_buckets,
        'centres_glance': centres_glance,
    })
