from .core import (
    StateCoreBootstrapMixin,
    StateCoreFixtureEffectsMixin,
    StateCoreFixtureStoreMixin,
    StateCoreMetadataMixin,
    StateCoreRenderMixin,
)
from .playback import (
    StatePlaybackChannelMixin,
    StatePlaybackPreviewControlMixin,
    StatePlaybackPreviewRunnerMixin,
    StatePlaybackPreviewStartMixin,
    StatePlaybackTransportMixin,
)
from .song import StateSongChaserMixin, StateSongCueMixin, StateSongLoadingMixin, StateSongSectionsMixin


class StateManager(
    StateSongSectionsMixin,
    StateSongChaserMixin,
    StateSongCueMixin,
    StateSongLoadingMixin,
    StatePlaybackTransportMixin,
    StatePlaybackPreviewRunnerMixin,
    StatePlaybackPreviewControlMixin,
    StatePlaybackPreviewStartMixin,
    StatePlaybackChannelMixin,
    StateCoreRenderMixin,
    StateCoreMetadataMixin,
    StateCoreFixtureStoreMixin,
    StateCoreFixtureEffectsMixin,
    StateCoreBootstrapMixin,
):
    pass
