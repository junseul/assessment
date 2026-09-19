from django import forms
from django.contrib import admin
from django.core import signing
from django.http import JsonResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_http_methods

from .simulation import PERSONAS, TASKS, advance, new_run
from .simulation_llm import MODELS, SimulationError, credentials


class SimulationForm(forms.Form):
    model = forms.ChoiceField(label='모델', choices=list(MODELS.items()))
    profile = forms.ChoiceField(label='가상 응시자', choices=[(k, v[0]) for k, v in PERSONAS.items()])
    persona = forms.CharField(label='추가 행동 특성 (실제 개인정보 입력 금지)', required=False,
                              max_length=1000, widget=forms.Textarea(attrs={'rows': 2}))
    task = forms.ChoiceField(label='검사', choices=[('all', '성향파악 + 전략게임 9종')] + list(TASKS.items()))
    mode = forms.ChoiceField(label='실행 범위', choices=[('quick', '항목당 5회 · 연결/동작 확인'), ('full', '전체 문항/시행')])
    seed = forms.IntegerField(label='상황 생성 시드', initial=42, min_value=0, max_value=2147483647)


SALT = 'local-llm-simulation-v1'


@never_cache
@require_http_methods(['GET', 'POST'])
def simulation_page(request):
    # Invoked only inside local_test's staff + DEBUG gates, before candidate/session writes.
    if request.method == 'GET':
        return render(request, 'invites/admin_simulation.html', {
            **admin.site.each_context(request), 'title': 'AI 시뮬레이션', 'form': SimulationForm(),
        })
    action = request.POST.get('action')
    if action == 'start':
        form = SimulationForm(request.POST)
        if not form.is_valid():
            return JsonResponse({'error': '입력값을 확인하세요.', 'fields': form.errors.get_json_data()}, status=400)
        data = form.cleaned_data
        try:
            credentials(data['model'])
        except SimulationError as exc:
            return JsonResponse({'error': str(exc)}, status=400)
        persona = PERSONAS[data['profile']][1] + '\n' + data['persona']
        state = new_run(data['model'], persona, data['task'], data['mode'], data['seed'], request.user.pk)
        return JsonResponse({
            'state': signing.dumps(state, salt=SALT, compress=True),
            'total': sum(state['limits'].values()),
            'metadata': {k: state[k] for k in ('id', 'model', 'persona', 'seed', 'mode', 'limits')},
        })
    if action != 'step':
        return JsonResponse({'error': '지원하지 않는 동작입니다.'}, status=400)
    token = request.POST.get('state', '')
    if not token or len(token) > 1000000:
        return JsonResponse({'error': '실행 상태가 유효하지 않습니다.'}, status=400)
    try:
        state = signing.loads(token, salt=SALT, max_age=86400)
    except signing.BadSignature:
        return JsonResponse({'error': '실행 상태가 변조되었거나 만료되었습니다. 새로 시작하세요.'}, status=400)
    if state['user_id'] != request.user.pk or state['version'] != 1:
        return JsonResponse({'error': '이 실행 상태에 접근할 수 없습니다.'}, status=403)
    if state['task_index'] >= len(state['tasks']):
        return JsonResponse({'error': '이미 완료된 실행입니다.'}, status=400)
    try:
        row, completed = advance(state)
    except SimulationError as exc:
        return JsonResponse({'error': str(exc)}, status=502)
    return JsonResponse({
        'state': signing.dumps(state, salt=SALT, compress=True),
        'row': row, 'completed': completed,
        'done': state['task_index'] == len(state['tasks']),
    })
