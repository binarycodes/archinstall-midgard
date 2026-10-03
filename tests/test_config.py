from installer import manifest, paths
from installer.config import Config


def test_config_reads_every_field_from_the_manifest():
    cfg = Config.from_manifest(manifest.load(paths.MANIFEST))
    assert cfg.username == "sujoy"
    assert not hasattr(cfg, "hostname")
    assert not hasattr(cfg, "disk")
