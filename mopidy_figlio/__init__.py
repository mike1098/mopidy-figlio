import logging
import pathlib

from mopidy import config, ext

__version__ = "0.0.1"


logger = logging.getLogger(__name__)


class Extension(ext.Extension):

    dist_name = "Mopidy-Figlio"
    ext_name = "Figlio"
    version = __version__

    def get_default_config(self):
        return config.read(pathlib.Path(__file__).parent / "ext.conf")

    def get_config_schema(self):
        schema = super().get_config_schema()
        return schema

    def setup(self, registry):
        from .frontend import FiglioFrontend
        registry.add("frontend", FiglioFrontend)
