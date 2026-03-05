from klayout_mcp.session_store import SessionStore


def test_session_store_closes_and_deletes_artifacts(tmp_path):
    store = SessionStore(tmp_path, ttl_seconds=3600)
    session = store.create_dummy_session()

    assert session.artifact_dir.exists()

    result = store.close(session.session_id)

    assert result["closed"] is True
    assert result["artifact_dir_deleted"] is True
    assert not session.artifact_dir.exists()
