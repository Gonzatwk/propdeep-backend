from types import SimpleNamespace

import httpx

from propdeep import mailer


def _settings(**kw):
    base = dict(resend_api_key="", smtp_host="", smtp_port=587, smtp_user="", smtp_password="",
                mail_from="PropDeep <acceso@propdeep.test>")
    return SimpleNamespace(**{**base, **kw})


def test_resend_is_used_when_there_is_a_key(monkeypatch):
    calls = []

    def fake_post(url, **kw):
        calls.append((url, kw))
        return httpx.Response(200, json={"id": "x"}, request=httpx.Request("POST", url))

    monkeypatch.setattr(mailer.httpx, "post", fake_post)
    monkeypatch.setattr(mailer.smtplib, "SMTP", lambda *a, **k: (_ for _ in ()).throw(AssertionError("SMTP")))
    mailer.send_login_link(_settings(resend_api_key="re_test", smtp_host="smtp.example.com"),
                           "ana@example.com", "https://propdeep.pages.dev/entrar?token=abc")
    (url, kw), = calls
    assert url == "https://api.resend.com/emails"
    assert kw["headers"] == {"Authorization": "Bearer re_test"}
    assert kw["json"]["from"] == "PropDeep <acceso@propdeep.test>" and kw["json"]["to"] == ["ana@example.com"]
    assert "token=abc" in kw["json"]["text"] and kw["json"]["subject"].startswith("Tu enlace")


def test_resend_errors_do_not_raise(monkeypatch, caplog):
    def fake_post(url, **kw):
        return httpx.Response(403, text="domain not verified", request=httpx.Request("POST", url))

    monkeypatch.setattr(mailer.httpx, "post", fake_post)
    assert mailer._send(_settings(resend_api_key="re_test"), "ana@example.com", "Hola", "cuerpo") is False
    assert "domain not verified" in caplog.text
    assert mailer._send(_settings(resend_api_key="re_test", mail_from=""), "ana@example.com", "Hola", "c") is False


def test_without_mail_settings_the_link_goes_to_the_log(caplog):
    mailer.send_login_link(_settings(), "ana@example.com", "https://x/entrar?token=abc")
    assert "token=abc" in caplog.text
