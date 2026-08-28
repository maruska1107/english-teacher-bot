from app.zoom.transcripts import _with_download_token


def test_with_download_token_adds_access_token_query_parameter():
    url = _with_download_token("https://zoom.example/rec/webhook_download/path?foo=bar", "download-token")

    assert url == "https://zoom.example/rec/webhook_download/path?foo=bar&access_token=download-token"


def test_with_download_token_replaces_existing_access_token_parameter():
    url = _with_download_token("https://zoom.example/rec/webhook_download/path?access_token=old", "new-token")

    assert url == "https://zoom.example/rec/webhook_download/path?access_token=new-token"
