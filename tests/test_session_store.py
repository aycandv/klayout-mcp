from klayout_mcp.models import LayerRef, MicronBox, SessionRuntime, ShapeRecord
from klayout_mcp.session_store import SessionStore


def test_session_store_closes_and_deletes_artifacts(tmp_path):
    store = SessionStore(tmp_path, ttl_seconds=3600)
    session = store.create_dummy_session()

    assert session.artifact_dir.exists()

    result = store.close(session.session_id)

    assert result["closed"] is True
    assert result["artifact_dir_deleted"] is True
    assert not session.artifact_dir.exists()


def test_session_runtime_evicts_oldest_shape_refs():
    runtime = SessionRuntime(
        layout=None,
        layers=[],
        selected_top_cell="TOP",
        top_cells=["TOP"],
        view={},
        max_shape_refs=2,
    )
    records = [_shape_record(f"shp_{index}") for index in range(3)]

    runtime.remember_shape(records[0])
    runtime.remember_shape(records[1])
    runtime.remember_shape(records[0])
    runtime.remember_shape(records[2])

    assert runtime.get_shape("shp_0") is records[0]
    assert runtime.get_shape("shp_1") is None
    assert runtime.get_shape("shp_2") is records[2]


def _shape_record(shape_id: str) -> ShapeRecord:
    return ShapeRecord(
        id=shape_id,
        kind="box",
        cell="TOP",
        leaf_cell="TOP",
        instance_path=("TOP",),
        layer=LayerRef(layer=1, datatype=0),
        bbox_um=MicronBox(0.0, 0.0, 1.0, 1.0),
        bbox_dbu=(0, 0, 1000, 1000),
    )
