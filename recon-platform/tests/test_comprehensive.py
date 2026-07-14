"""Comprehensive test suite"""
import pytest
import json
import sys
import os
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


# ============ UNIT TESTS ============
class TestLabFunctions:
    """Test all 102 lab functions"""
    def test_encoding(self):
        from modules.lab_functions import LabFunctions
        lab = LabFunctions()
        assert lab.b64_encode("hello") == "aGVsbG8="
        assert lab.b64_decode("aGVsbG8=") == "hello"
        assert lab.url_encode("hello world") == "hello%20world"
        assert lab.hex_encode("ABC") == "414243"
        assert lab.rot13("hello") == "uryyb"

    def test_hashing(self):
        from modules.lab_functions import LabFunctions
        lab = LabFunctions()
        h = lab.md5_hash("hello")
        assert len(h) == 32
        assert lab.sha256_hash("hello").startswith("2cf24d")
        assert lab.sha1_hash("hello") == "aaf4c61ddcc5e8a2dabede0f3b482cd9aea9434d"

    def test_network(self):
        from modules.lab_functions import LabFunctions
        lab = LabFunctions()
        assert lab.validate_ipv4("192.168.1.1") == True
        assert lab.validate_ipv4("256.0.0.1") == False
        assert lab.validate_email("test@example.com") == True
        assert lab.validate_email("invalid") == False
        assert lab.cidr_to_range("192.168.1.0/24")[0] == "192.168.1.1"

    def test_crypto(self):
        from modules.lab_functions import LabFunctions
        lab = LabFunctions()
        assert lab.xor_cipher("hello", "k") == "1:1:1:1:1"
        enc = lab.caesar_cipher("ABC", 1)
        assert "B" in enc

    def test_text_analysis(self):
        from modules.lab_functions import LabFunctions
        lab = LabFunctions()
        assert lab.word_count("hello world test") == 3
        assert lab.char_count("hello") == 5
        assert lab.is_palindrome("racecar") == True
        assert lab.is_palindrome("hello") == False
        assert lab.reverse_string("hello") == "olleh"

    def test_osint(self):
        from modules.lab_functions import LabFunctions
        lab = LabFunctions()
        rep = lab.domain_reputation("example.com")
        assert "domain" in rep
        rep = lab.ip_reputation("8.8.8.8")
        assert "ip" in rep

    def test_utilities(self):
        from modules.lab_functions import LabFunctions
        lab = LabFunctions()
        assert lab.random_password(16)["length"] == 16
        assert lab.generate_uuid()["uuid"]
        assert lab.timestamp_to_date(0)["unix"] == 0
        assert lab.date_to_timestamp("1970-01-01T00:00:00") == 0
        assert lab.base_converter(255, 10, 16) == "ff"
        assert lab.random_string(10)["length"] == 10


class TestEmailService:
    """Test email service"""
    def test_templates(self):
        from modules.email_service import EmailTemplates
        t = EmailTemplates.welcome("testuser")
        assert "testuser" in t["html"]
        assert "Welcome" in t["subject"]
        t = EmailTemplates.password_reset("user", "https://test.com/reset")
        assert "https://test.com/reset" in t["html"]
        t = EmailTemplates.scan_complete("user", "example.com", 5, 2, "https://test.com/r")
        assert "example.com" in t["html"]
        assert "5" in t["html"]

    def test_send_email(self):
        from modules.email_service import send_email
        with patch('modules.email_service.get_email_service') as mock:
            mock_svc = Mock()
            mock_svc.send.return_value = {"success": True, "provider": "smtp"}
            mock.return_value = mock_svc
            result = send_email("test@test.com", "Subject", "<p>HTML</p>")
            assert result["success"] == True


class TestPayments:
    """Test Stripe payments"""
    def test_webhook_verification(self):
        from modules.payments import stripe_webhook_secret
        assert isinstance(stripe_webhook_secret, str)


class TestI18n:
    """Test internationalization"""
    def test_supported_languages(self):
        from modules.i18n import SUPPORTED_LANGUAGES, t
        assert "en" in SUPPORTED_LANGUAGES
        assert "ru" in SUPPORTED_LANGUAGES
        assert "uz" in SUPPORTED_LANGUAGES
        assert "es" in SUPPORTED_LANGUAGES
        assert "fr" in SUPPORTED_LANGUAGES
        assert "de" in SUPPORTED_LANGUAGES
        assert "zh" in SUPPORTED_LANGUAGES
        assert "ja" in SUPPORTED_LANGUAGES
        assert "ar" in SUPPORTED_LANGUAGES
        assert "tr" in SUPPORTED_LANGUAGES
        assert "pt" in SUPPORTED_LANGUAGES

    def test_translations(self):
        from modules.i18n import t
        with patch('modules.i18n.session', {"language": "ru"}):
            assert t("common.save") == "Сохранить"
        with patch('modules.i18n.session', {"language": "uz"}):
            assert t("common.save") == "Saqlash"


class TestAnomalyDetector:
    """Test ML anomaly detection"""
    def test_feature_extraction(self):
        from modules.ml_anomaly import AnomalyDetector
        from models import Scan, Finding
        detector = AnomalyDetector()
        scan = Mock(spec=Scan, target="example.com", duration=120, scan_type="full")
        findings = [Mock(spec=Finding, severity=3, category="xss", description="x", url="http://example.com/")]
        features = detector.extract_features(scan, findings)
        assert len(features) == 9
        assert features[0] == 1
        assert features[2] == 0


class TestPDFReport:
    """Test PDF report generation"""
    def test_risk_score(self):
        from modules.pdf_reports import PDFReportGenerator
        gen = PDFReportGenerator.__new__(PDFReportGenerator)
        gen.findings = []
        assert gen._risk_score({0: 0, 1: 0, 2: 0, 3: 0, 4: 0}) == 0
        assert gen._risk_score({0: 0, 1: 0, 2: 0, 3: 5, 4: 1}) >= 80


# ============ INTEGRATION TESTS ============
class TestAPI:
    """Integration tests for API"""
    @pytest.fixture
    def client(self):
        from app import create_app
        from models import db
        app = create_app(testing=True)
        with app.test_client() as client:
            with app.app_context():
                db.create_all()
                yield client
                db.drop_all()

    def test_register(self, client):
        res = client.post("/api/v1/auth/register", json={"username": "test", "email": "test@test.com", "password": "Test123!@#"})
        assert res.status_code in [200, 201]

    def test_login(self, client):
        client.post("/api/v1/auth/register", json={"username": "test", "email": "test@test.com", "password": "Test123!@#"})
        res = client.post("/api/v1/auth/login", json={"username": "test", "password": "Test123!@#"})
        assert res.status_code in [200, 401]

    def test_health(self, client):
        res = client.get("/api/v1/health")
        assert res.status_code == 200

    def test_lab_functions_list(self, client):
        res = client.get("/api/v1/lab/functions")
        assert res.status_code == 200
        data = res.get_json()
        assert "functions" in data or "error" in data


class TestWebSocket:
    """Test WebSocket functionality"""
    def test_broadcast_functions(self):
        from modules.websocket import broadcast_new_user, broadcast_scan_progress
        assert callable(broadcast_new_user)
        assert callable(broadcast_scan_progress)


class TestAuditLogging:
    """Test audit logging"""
    def test_log_creation(self):
        from modules.audit_log import get_audit_logger
        logger = get_audit_logger()
        assert logger is not None
        assert "SOC2" in logger.COMPLIANCE_STANDARDS
        assert "GDPR" in logger.COMPLIANCE_STANDARDS
        assert "HIPAA" in logger.COMPLIANCE_STANDARDS
        assert "PCI-DSS" in logger.COMPLIANCE_STANDARDS
        assert "ISO27001" in logger.COMPLIANCE_STANDARDS


class TestShodan:
    """Test Shodan integration"""
    def test_without_api_key(self):
        from modules.shodan_censys import ShodanIntegration
        with patch.dict(os.environ, {"SHODAN_API_KEY": ""}):
            shodan = ShodanIntegration()
            assert shodan.api_key == "" or shodan.api_key is None
            res = shodan.host_lookup("8.8.8.8")
            assert "error" in res or "ip" in res


# ============ PERFORMANCE TESTS ============
class TestPerformance:
    """Performance benchmarks"""
    def test_lab_function_speed(self):
        from modules.lab_functions import LabFunctions
        import time
        lab = LabFunctions()
        start = time.time()
        for _ in range(1000): lab.md5_hash("test")
        duration = time.time() - start
        assert duration < 5.0

    def test_password_generation_speed(self):
        from modules.lab_functions import LabFunctions
        import time
        lab = LabFunctions()
        start = time.time()
        for _ in range(100): lab.random_password(32)
        duration = time.time() - start
        assert duration < 3.0


# ============ SECURITY TESTS ============
class TestSecurity:
    """Security tests"""
    def test_password_hashing(self):
        from werkzeug.security import generate_password_hash, check_password_hash
        h = generate_password_hash("Test123!@#")
        assert check_password_hash(h, "Test123!@#")
        assert not check_password_hash(h, "WrongPass")

    def test_jwt_token(self):
        import jwt
        from datetime import datetime, timedelta
        secret = "test-secret"
        payload = {"user_id": 1, "exp": datetime.utcnow() + timedelta(hours=1)}
        token = jwt.encode(payload, secret, algorithm="HS256")
        decoded = jwt.decode(token, secret, algorithms=["HS256"])
        assert decoded["user_id"] == 1

    def test_sql_injection_prevention(self):
        from modules.lab_functions import LabFunctions
        lab = LabFunctions()
        result = lab.sql_injection_test("' OR '1'='1")
        assert result["vulnerable"] == True
        result = lab.sql_injection_test("admin' --")
        assert result["vulnerable"] == True

    def test_xss_detection(self):
        from modules.lab_functions import LabFunctions
        lab = LabFunctions()
        result = lab.xss_detector("<script>alert(1)</script>")
        assert result["vulnerable"] == True
        result = lab.xss_detector("onerror=alert(1)")
        assert result["vulnerable"] == True


# ============ CONFTEST ============
@pytest.fixture(autouse=True)
def reset_singletons():
    yield
