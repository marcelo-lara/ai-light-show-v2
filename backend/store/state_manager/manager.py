from .core import (
    StateCoreBootstrapMixin,
    StateCoreFixtureEffectsMixin,
    StateCoreFixtureStoreMixin,
    StateCoreMetadataMixin,
    StateCoreRenderMixin,
)
from .playback import (
    StatePlaybackChannelMixin,
    StatePlaybackPreviewChaserMixin,
    StatePlaybackPreviewControlMixin,
    StatePlaybackPreviewRunnerMixin,
    StatePlaybackPreviewStartMixin,
    StatePlaybackTransportMixin,
)
from .song import StateSongChaserMixin, StateSongCueMixin, StateSongLoadingMixin, StateSongSectionsMixin
from .song import StateSongHintsMixin


class StateManager(
    StateSongSectionsMixin,
    StateSongChaserMixin,
    StateSongCueMixin,
    StateSongHintsMixin,
    StateSongLoadingMixin,
    StatePlaybackTransportMixin,
    StatePlaybackPreviewChaserMixin,
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
