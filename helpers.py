from datetime import date

from invites.models import Candidate


def make_candidate(**overrides):
    data = {
        'name': '홍길동',
        'birthdate': date(1990, 1, 15),
        'phone': '010-1234-5678',
        'email': 'hong@example.com',
    }
    data.update(overrides)
    return Candidate.objects.create(**data)


def login_candidate(client, candidate=None):
    candidate = candidate or make_candidate()
    session = client.session
    session['candidate_id'] = candidate.id
    session['candidate_name'] = candidate.name
    session['candidate_email'] = candidate.email
    session.save()
    return candidate
