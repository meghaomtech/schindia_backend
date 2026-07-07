"""
Dashboard / Info endpoint — aggregate statistics across all centres.
Matches the /admin/info page on the frontend.
"""
from django.db.models import Count, Q
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from schindia_auth.permissions import IsApprovedUser
from dynamo_backend.router import use_dynamo
from centres.models import Centre, Room
from sessions_app.models import Session, SessionSlot
from children.models import Child, ChildEnrolment
from roles.models import Role, RoleMember
from django.contrib.auth import get_user_model

User = get_user_model()


@api_view(['GET'])
@permission_classes([IsAuthenticated, IsApprovedUser])
def info_dashboard(request):
    """
    A snapshot across all centres — children, teachers, sessions, roles and capacity.
    Works with both Django ORM (local) and DynamoDB (production).
    """
    if use_dynamo():
        return _info_dashboard_dynamo(request)

    # Django ORM path
    centres = Centre.objects.prefetch_related('rooms', 'sessions', 'roles').all()

    total_centres = centres.count()
    total_children = Child.objects.count()
    total_sessions = Session.objects.count()
    total_rooms = Room.objects.count()
    total_enrolments = ChildEnrolment.objects.count()
    total_roles = Role.objects.count()
    total_people = RoleMember.objects.values('user').distinct().count()

    # Count teachers (users assigned to 'Teacher' role)
    total_teachers = RoleMember.objects.filter(
        role__name__icontains='teacher'
    ).values('user').distinct().count()

    # Children & teachers per centre
    children_per_centre = []
    for centre in centres:
        children_count = Child.objects.filter(centre=centre).count()
        teachers_count = RoleMember.objects.filter(
            role__centre=centre,
            role__name__icontains='teacher'
        ).values('user').distinct().count()
        children_per_centre.append({
            'centre_id': str(centre.id),
            'centre_name': centre.name,
            'children': children_count,
            'teachers': teachers_count,
        })

    # Roles & people breakdown
    role_breakdown = Role.objects.values('name').annotate(
        people_count=Count('members__user', distinct=True)
    ).order_by('name')

    roles_people = []
    for r in role_breakdown:
        roles_people.append({
            'role': r['name'],
            'people': r['people_count'],
        })

    # Per-centre role/people summary
    per_centre_roles = []
    for centre in centres:
        people_count = RoleMember.objects.filter(
            role__centre=centre
        ).values('user').distinct().count()
        roles_count = Role.objects.filter(centre=centre).count()
        per_centre_roles.append({
            'centre_id': str(centre.id),
            'centre_name': centre.name,
            'people': people_count,
            'roles': roles_count,
        })

    # Session popularity (enrolments per session)
    session_popularity = []
    for session in Session.objects.all():
        enrolment_count = ChildEnrolment.objects.filter(
            slot__session=session
        ).values('child').distinct().count()
        session_popularity.append({
            'session_id': str(session.id),
            'session_name': session.name,
            'enrolments': enrolment_count,
        })
    session_popularity.sort(key=lambda x: x['enrolments'], reverse=True)

    # Age distribution
    from datetime import date
    today = date.today()
    age_buckets = {'0-1y': 0, '1-2y': 0, '2-3y': 0, '3-4y': 0, '4-5y': 0, '5y+': 0}
    for child in Child.objects.all():
        age_days = (today - child.date_of_birth).days
        age_years = age_days / 365.25
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

    # Centres at a glance
    centres_glance = []
    for centre in centres:
        rooms_count = centre.rooms.count()
        sessions_count = Session.objects.filter(centre=centre).count()
        slots_count = SessionSlot.objects.filter(centre=centre).count()
        children_count = Child.objects.filter(centre=centre).count()
        roles_count = Role.objects.filter(centre=centre).count()
        people_count = RoleMember.objects.filter(
            role__centre=centre
        ).values('user').distinct().count()

        has_schedule = slots_count > 0
        centres_glance.append({
            'centre_id': str(centre.id),
            'centre_name': centre.name,
            'rooms': rooms_count,
            'sessions': sessions_count,
            'slots': slots_count,
            'children': children_count,
            'roles': roles_count,
            'people': people_count,
            'status': 'Active' if has_schedule else 'No schedule',
        })

    return Response({
        'summary': {
            'centres': total_centres,
            'children': total_children,
            'teachers': total_teachers,
            'sessions': total_sessions,
            'rooms': total_rooms,
            'enrolments': total_enrolments,
            'roles': total_roles,
            'people': total_people,
        },
        'children_per_centre': children_per_centre,
        'roles_people': roles_people,
        'per_centre_roles': per_centre_roles,
        'session_popularity': session_popularity,
        'age_distribution': age_buckets,
        'centres_glance': centres_glance,
    })


def _info_dashboard_dynamo(request):
    """DynamoDB-based info dashboard for production."""
    from dynamo_backend.services import (
        centres_db, sessions_db, children_db, roles_db
    )
    from datetime import date as date_type

    centres = centres_db.list_centres()
    all_children = children_db.list_children()
    total_centres = len(centres)
    total_children = len(all_children)

    # Aggregate data
    total_rooms = sum(len(c.get('rooms', [])) for c in centres)
    total_sessions = 0
    total_enrolments = 0
    total_roles = 0
    total_people = set()
    total_teachers = set()

    children_per_centre = []
    per_centre_roles = []
    centres_glance = []
    session_popularity = []

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

        # Count teachers and people
        centre_people = set()
        teachers_count = 0
        for role in roles:
            for member in role.get('members', []):
                uid = member.get('user_id')
                if uid:
                    centre_people.add(uid)
                    total_people.add(uid)
                    if 'teacher' in role.get('name', '').lower():
                        total_teachers.add(uid)
                        teachers_count += 1

        children_per_centre.append({
            'centre_id': cid,
            'centre_name': centre.get('name', ''),
            'children': children_count,
            'teachers': teachers_count,
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

    # Roles breakdown
    roles_people = {}
    for centre in centres:
        cid = centre['id']
        roles = roles_db.list_roles(cid)
        for role in roles:
            name = role.get('name', 'Unknown')
            member_count = len(role.get('members', []))
            if name not in roles_people:
                roles_people[name] = 0
            roles_people[name] += member_count

    roles_people_list = [{'role': k, 'people': v} for k, v in roles_people.items()]

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
