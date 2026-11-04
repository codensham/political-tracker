from tracker.config import get_key, load_dotenv


def test_env_var_beats_dotenv(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("FEC_API_KEY=from-file\n", encoding="utf-8")
    monkeypatch.setenv("FEC_API_KEY", "from-env")
    assert get_key("FEC_API_KEY", root=tmp_path) == "from-env"


def test_dotenv_used_when_env_unset(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("FEC_API_KEY=from-file\n", encoding="utf-8")
    monkeypatch.delenv("FEC_API_KEY", raising=False)
    assert get_key("FEC_API_KEY", root=tmp_path) == "from-file"


def test_blank_value_is_unset(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("FEC_API_KEY=\n", encoding="utf-8")
    monkeypatch.delenv("FEC_API_KEY", raising=False)
    assert get_key("FEC_API_KEY", root=tmp_path) is None


def test_comments_and_blank_lines_ignored(tmp_path):
    (tmp_path / ".env").write_text("# a comment\n\nFEC_API_KEY\nCONGRESS_API_KEY=abc\n", encoding="utf-8")
    assert load_dotenv(tmp_path) == {"CONGRESS_API_KEY": "abc"}


def test_quotes_stripped(tmp_path):
    (tmp_path / ".env").write_text('X_KEY="quoted"\n', encoding="utf-8")
    assert load_dotenv(tmp_path) == {"X_KEY": "quoted"}


def test_missing_dotenv_returns_none(tmp_path, monkeypatch):
    monkeypatch.delenv("FEC_API_KEY", raising=False)
    assert get_key("FEC_API_KEY", root=tmp_path) is None


def test_fec_collector_uses_key_and_falls_back_to_demo(tmp_path, monkeypatch):
    from tracker.collectors.fec import FecFinanceCollector

    monkeypatch.delenv("FEC_API_KEY", raising=False)
    (tmp_path / ".env").write_text("FEC_API_KEY=file-key\n", encoding="utf-8")
    monkeypatch.setattr("tracker.config.REPO_ROOT", tmp_path)
    assert FecFinanceCollector()._api_key == "file-key"

    (tmp_path / ".env").write_text("FEC_API_KEY=\n", encoding="utf-8")
    assert FecFinanceCollector()._api_key == "DEMO_KEY"
