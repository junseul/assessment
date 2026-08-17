from functools import wraps

from django.shortcuts import redirect

from .models import Candidate


def candidate_required(view_func):
    """Only let a session that passed invite verification reach the assessment views."""
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        candidate = Candidate.objects.filter(pk=request.session.get('candidate_id')).first()
        if candidate is None:
            return redirect('invites:no_access')
        request.candidate = candidate
        return view_func(request, *args, **kwargs)
    return wrapper
