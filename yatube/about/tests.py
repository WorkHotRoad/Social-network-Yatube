from django.test import Client, TestCase


class StaticURLTests(TestCase):
    def setUp(self):
        self.guest_client = Client()

    def test_all_pages(self):
        pages = ['/about/author/', '/about/tech/']
        '''Проверяем доступность страниц приложения about'''
        for key in pages:
            response = self.guest_client.get(key)
            with self.subTest(key=key):
                self.assertEqual(response.status_code, 200)

    def test_urls_about_correct_tempalate(self):
        ''' проверка соответствия URL-адресов и шаблонов about '''
        template_urls_name = {
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html'
        }
        for template, address in template_urls_name.items():
            with self.subTest(template=template):
                response = self.guest_client.get(template)
                self.assertTemplateUsed(response, address)
