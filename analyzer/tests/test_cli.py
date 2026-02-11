def test_listen_command_registered():
    from song_analyzer import cli

    commands = [c.name for c in cli.app.registered_commands]
    assert "listen" in commands, "listen command should be registered on the CLI"
