import { Layout } from "./Layout.ts";
import { PlaybackReadout } from "./PlaybackReadout.ts";
import { PlayerOptions, ZoomControl } from "./PlayerOptions.ts";
import { TransportControls } from "./TransportControls.ts";
import { Waveform } from "./Waveform.ts";

export type SongPlayerUiCallbacks = {
	onPrevSection: () => void;
	onPrevBeat: () => void;
	onStop: () => void;
	onPlayPause: () => void;
	onNextBeat: () => void;
	onNextSection: () => void;
	onLoopToggle: (checked: boolean) => void;
	onShowSectionsToggle: (checked: boolean) => void;
	onShowDownbeatsToggle: (checked: boolean) => void;
	onZoom: (value: number) => void;
};

export type SongPlayerUi = {
	root: HTMLElement;
	waveform: HTMLElement;
	songLabelEl: HTMLElement;
	barBeatEl: HTMLElement;
	positionEl: HTMLElement;
	updatePlayPauseIcon: (playing: boolean) => void;
	zoomInput: HTMLInputElement;
	showRegionsInput: HTMLInputElement;
	showDownbeatsInput: HTMLInputElement;
	prevSectionBtn: HTMLButtonElement;
	prevBeatBtn: HTMLButtonElement;
	nextBeatBtn: HTMLButtonElement;
	nextSectionBtn: HTMLButtonElement;
	loopToggle: HTMLInputElement;
	zoomDispose: () => void;
};

export function buildSongPlayerUi(callbacks: SongPlayerUiCallbacks): SongPlayerUi {
	const { container: waveformContainer, wave: waveform, title: songLabel } = Waveform();

	const {
		container: transportContainer,
		prevSectionBtn,
		prevBeatBtn,
		nextBeatBtn,
		nextSectionBtn,
		updatePlayPauseIcon,
	} = TransportControls({
		onPrevSection: callbacks.onPrevSection,
		onPrevBeat: callbacks.onPrevBeat,
		onStop: callbacks.onStop,
		onPlayPause: callbacks.onPlayPause,
		onNextBeat: callbacks.onNextBeat,
		onNextSection: callbacks.onNextSection,
	});

	const { barBeatEl, positionEl } = PlaybackReadout();

	const {
		container: optionsContainer,
		loopToggle,
		showSectionsToggle,
		showDownbeatsToggle,
	} = PlayerOptions({
		onLoopToggle: callbacks.onLoopToggle,
		onShowSectionsToggle: callbacks.onShowSectionsToggle,
		onShowDownbeatsToggle: callbacks.onShowDownbeatsToggle,
	});

	const { container: zoomContainer, zoomSlider, dispose: zoomDispose } = ZoomControl({
		initialZoom: 40,
		onZoom: callbacks.onZoom,
	});

	const root = Layout({
		waveform: waveformContainer,
		barBeat: barBeatEl,
		transport: transportContainer,
		options: optionsContainer,
		zoom: zoomContainer,
		position: positionEl,
	});

	return {
		root,
		waveform,
		songLabelEl: songLabel,
		barBeatEl,
		positionEl,
		updatePlayPauseIcon,
		zoomInput: zoomSlider,
		showRegionsInput: showSectionsToggle,
		showDownbeatsInput: showDownbeatsToggle,
		prevSectionBtn,
		prevBeatBtn,
		nextBeatBtn,
		nextSectionBtn,
		loopToggle,
		zoomDispose,
	};
}
