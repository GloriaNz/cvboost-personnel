import json
import io
import os
import unittest
import tempfile
from werkzeug.datastructures import FileStorage
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.test import EnvironBuilder, stream_encode_multipart
from flask import request

from werkzeug.security import generate_password_hash

from app import create_app, db
from app.models import User


class SecurityTests(unittest.TestCase):
    def setUp(self):
        self.temp_directory = tempfile.TemporaryDirectory()
        self.app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'test-secret-key',
            'SQLALCHEMY_DATABASE_URI': 'sqlite://',
            'WTF_CSRF_ENABLED': False,
            'UPLOAD_FOLDER': os.path.join(self.temp_directory.name, 'files'),
            'UPLOAD_AUDIT_LOG': os.path.join(self.temp_directory.name, 'audit', 'uploads.jsonl'),
        })
        self.client = self.app.test_client()
        with self.app.app_context():
            db.create_all()
            user = User(
                nom='Test',
                prenom='Utilisateur',
                email='test@example.com',
                password_hash=generate_password_hash('password-test')
            )
            db.session.add(user)
            db.session.commit()

    def tearDown(self):
        with self.app.app_context():
            db.session.remove()
            db.drop_all()
        self.temp_directory.cleanup()

    def test_upload_limits_and_extensions(self):
        self.assertEqual(self.app.config['MAX_UPLOAD_SIZE'], 5 * 1024 * 1024)
        self.assertLessEqual(self.app.config['MAX_CONTENT_LENGTH'], 6 * 1024 * 1024)
        self.assertEqual(self.app.config['ALLOWED_EXTENSIONS'], {'pdf', 'docx'})

    def test_proxy_headers_are_trusted_only_when_configured(self):
        self.assertNotIsInstance(self.app.wsgi_app, ProxyFix)

        proxied_app = create_app({
            'TESTING': True,
            'SECRET_KEY': 'test-secret-key',
            'SQLALCHEMY_DATABASE_URI': 'sqlite://',
            'WTF_CSRF_ENABLED': False,
            'UPLOAD_FOLDER': os.path.join(self.temp_directory.name, 'proxy-files'),
            'UPLOAD_AUDIT_LOG': os.path.join(
                self.temp_directory.name,
                'proxy-audit',
                'uploads.jsonl',
            ),
            'TRUST_PROXY': True,
        })
        self.assertIsInstance(proxied_app.wsgi_app, ProxyFix)

        @proxied_app.get('/_test/request-scheme')
        def request_scheme():
            return request.scheme

        response = proxied_app.test_client().get(
            '/_test/request-scheme',
            headers={'X-Forwarded-Proto': 'https'},
        )
        self.assertEqual(response.get_data(as_text=True), 'https')

    def test_auth_forms_use_gloria_nziengi_examples(self):
        login_page = self.client.get('/login')
        register_page = self.client.get('/register')

        self.assertIn(b'gloria.nziengi@email.com', login_page.data)
        self.assertIn(b'placeholder="Nziengi"', register_page.data)
        self.assertIn(b'placeholder="Gloria"', register_page.data)

    def log_in(self):
        return self.client.post(
            '/login',
            data={'email': 'test@example.com', 'password': 'password-test'},
        )

    def post_upload(self, filename, content):
        upload_stream = io.BytesIO(content)
        request_stream, content_length, boundary = stream_encode_multipart(
            {'cv': FileStorage(stream=upload_stream, filename=filename)},
            use_tempfile=False,
        )
        builder = EnvironBuilder(
            path='/upload',
            method='POST',
            input_stream=request_stream,
            content_length=content_length,
            content_type=f'multipart/form-data; boundary="{boundary}"',
        )
        try:
            return self.client.open(builder)
        finally:
            builder.close()
            request_stream.close()
            upload_stream.close()

    def test_login_rejects_external_next_url(self):
        response = self.client.post(
            '/login?next=https://example.org',
            data={'email': 'test@example.com', 'password': 'password-test'},
        )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.headers['Location'], '/')

    def test_logout_requires_post(self):
        self.client.post(
            '/login',
            data={'email': 'test@example.com', 'password': 'password-test'},
        )
        response = self.client.get('/logout')
        self.assertEqual(response.status_code, 405)

    def test_logout_post_clears_session(self):
        self.log_in()
        response = self.client.post('/logout')
        self.assertEqual(response.status_code, 302)
        self.assertEqual(self.client.get('/history').status_code, 302)

    def test_upload_rejects_doc_extension(self):
        self.log_in()
        response = self.post_upload('resume.doc', b'legacy document')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(os.listdir(self.app.config['UPLOAD_FOLDER']), [])

    def test_upload_rejects_file_over_five_megabytes(self):
        self.log_in()
        response = self.post_upload('resume.pdf', b'x' * (5 * 1024 * 1024 + 1))
        self.assertEqual(response.status_code, 413)
        self.assertEqual(os.listdir(self.app.config['UPLOAD_FOLDER']), [])

    def test_request_over_framework_limit_is_audited(self):
        self.log_in()
        response = self.post_upload('resume.pdf', b'x' * (6 * 1024 * 1024))
        self.assertEqual(response.status_code, 413)
        with open(self.app.config['UPLOAD_AUDIT_LOG'], encoding='utf-8') as audit_file:
            event = json.loads(audit_file.readline())
        self.assertEqual(event['reason'], 'request_too_large')
        self.assertEqual(event['outcome'], 'rejected')

    def test_upload_accepts_file_at_five_megabytes(self):
        self.log_in()
        pdf_content = b'%PDF-1.7\n' + b'x' * (5 * 1024 * 1024 - 9)
        response = self.post_upload('resume.pdf', pdf_content)
        self.assertEqual(response.status_code, 302)
        self.assertEqual(len(os.listdir(self.app.config['UPLOAD_FOLDER'])), 1)

    def test_upload_audit_logs_metadata_without_personal_filename(self):
        self.log_in()
        response = self.post_upload('Jean Dupont CV.pdf', b'%PDF-1.7 test')
        self.assertEqual(response.status_code, 302)

        with open(self.app.config['UPLOAD_AUDIT_LOG'], encoding='utf-8') as audit_file:
            event = json.loads(audit_file.readline())
        self.assertEqual(event['outcome'], 'accepted')
        self.assertEqual(event['extension'], 'pdf')
        self.assertEqual(event['size_bytes'], len(b'%PDF-1.7 test'))
        self.assertEqual(event['filename'], 'upload.pdf')
        self.assertNotIn('Jean Dupont', event['filename'])


if __name__ == '__main__':
    unittest.main()
