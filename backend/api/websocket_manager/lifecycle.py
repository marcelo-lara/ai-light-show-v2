def ensure_arm_state_initialized(manager) -> None:
    if manager.fixture_armed:
        return
    for fixture in manager.state_manager.fixtures:
        manager.fixture_armed[fixture.id] = True


def next_seq(manager) -> int:
    manager.seq += 1
    return manager.seq
