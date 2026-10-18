from fleetdata.extract import iter_rows, load_alias_map, select_hashes


def test_solo_salen_los_vehiculos_pedidos_en_todos_los_dias(fake_fleet):
    amap = load_alias_map(fake_fleet["alias_path"])
    hashes = select_hashes(amap, ["T01", "T03"])
    rows = list(iter_rows(fake_fleet["archive"], hashes))
    assert {amap[r["truck_hash"]] for r in rows} == {"T01", "T03"}
    assert {r["ems_time"][:10] for r in rows} == {f"2020-04-{d:02d}" for d in range(1, 20)}


def test_la_tabla_de_alias_se_recibe_por_argumento(fake_fleet):
    assert len(load_alias_map(fake_fleet["alias_path"])) == 6
