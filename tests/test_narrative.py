from types import SimpleNamespace

from propdeep.model import Context, analyze, compute_trends
from propdeep.narrative import template_report, write_report


def _analysis(side_values):
    t = compute_trends(side_values, [36.0] * len(side_values), 27.5, len(side_values))
    return analyze("Luka Doncic", "pts", 27.5, 1.9, 1.9, t, Context(opponent="Lakers", home=True))


class FakeClaude:
    def __init__(self, text="Informe.", stop_reason="end_turn", fail=False):
        self.calls = []
        self._text, self._stop, self._fail = text, stop_reason, fail
        self.beta = SimpleNamespace(messages=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        self.calls.append(kwargs)
        if self._fail:
            raise RuntimeError("caída")
        return SimpleNamespace(stop_reason=self._stop,
                               content=[SimpleNamespace(type="text", text=self._text)])


def test_template_never_promises():
    for values in ([34.0] * 20, [27.0] * 20):
        text = template_report(_analysis(values)).lower()
        assert "seguro" not in text and "garantiz" not in text


def test_template_is_analysis_not_a_pick():
    for values in ([34.0] * 20, [27.6] * 20, [20.0] * 20):
        text = template_report(_analysis(values))
        assert "orientativa" in text and "Superó la línea" in text
        for word in ("ventaja", "valor", "confianza", "recomendamos jugar"):
            assert word not in text.lower()


def test_claude_does_not_see_the_model_verdict():
    import json

    fake = FakeClaude()
    write_report(_analysis([34.0] * 20), fake, books=[{"bookmaker": "bookA", "line": 27.5}])
    data = json.loads(fake.calls[0]["messages"][0]["content"].split("\n", 1)[1])
    assert data["books"][0]["bookmaker"] == "bookA" and data["projection"]
    for key in ("side", "edge", "confidence", "expected_value", "prob_over_final"):
        assert key not in data


def test_claude_call_shape_and_fallbacks():
    fake = FakeClaude()
    assert write_report(_analysis([34.0] * 20), fake) == "Informe."
    call = fake.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default"
    assert "server-side-fallback-2026-07-01" in call["betas"]


def test_refusal_or_error_falls_back_to_template():
    a = _analysis([34.0] * 20)
    assert write_report(a, FakeClaude(stop_reason="refusal")) == template_report(a)
    assert write_report(a, FakeClaude(fail=True)) == template_report(a)
