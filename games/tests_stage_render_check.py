"""화면 렌더링 확인용 임시 테스트 (확인 후 삭제한다)."""
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from helpers import login_candidate


class StageRenderCheckTests(TestCase):
    def test_login_pages(self):
        login_html = Client().get(reverse('login')).content.decode()
        self.assertIn('class="login-page"', login_html)
        self.assertIn('class="card login-card"', login_html)
        self.assertNotIn('game-stage.css', login_html)

        admin_html = Client().get('/admin/login/').content.decode()
        self.assertIn('admin-login-card', admin_html)

    def test_game_page_assets(self):
        login_candidate(self.client)
        html = self.client.get(reverse('games:play', args=['radar-control'])).content.decode()
        self.assertEqual(html.count('css/game-stage.css'), 1)
        self.assertEqual(html.count('js/game-stage.js'), 1)
        self.assertEqual(html.count('js/game-three.js'), 1)
        self.assertIn('.game-three-canvas', html)
        self.assertIn('css/lightdash.css', html)

    def test_admin_grid_cards(self):
        get_user_model().objects.create_superuser('render-check', 'render-check@example.com', 'pw')
        staff = Client()
        staff.force_login(get_user_model().objects.get(username='render-check'))
        html = staff.get(reverse('games:admin_grid')).content.decode()
        self.assertIn('css/game-stage.css', html)
        self.assertEqual(html.count('game-select-card'), 9)
