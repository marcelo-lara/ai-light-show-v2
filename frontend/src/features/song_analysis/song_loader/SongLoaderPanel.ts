import { Card } from "../../../shared/components/layout/Card.ts";
import { List } from "../../../shared/components/layout/List.ts";
import { ConfirmCancelPrompt } from "../../../shared/components/feedback/ConfirmCancelPrompt.ts";
import { getBackendStore, subscribeBackendStore } from "../../../shared/state/backend_state.ts";
import { selectEditLock } from "../../../shared/state/selectors.ts";
import { loadSong, requestSongList } from "../song_analysis_intents.ts";
import { getSongLoaderState, subscribeSongLoaderState } from "./state.ts";

function createText(className: string, text: string): HTMLSpanElement {
	const node = document.createElement("span");
	node.className = className;
	node.textContent = text;
	return node;
}

export function SongLoaderPanel(): HTMLElement {
	const content = document.createElement("div");
	content.className = "song-loader-panel";
	const header = document.createElement("div");
	header.className = "song-loader-header";
	header.append(createText("song-loader-title", "Song Loader"), createText("song-loader-meta", "songs"));
	const body = document.createElement("div");
	body.className = "song-loader-body song-loader-list o-list";
	content.append(header, body);

	const render = () => {
		body.replaceChildren();
		const loadedSong = getBackendStore().state.song?.filename ?? "";
		const editLock = selectEditLock() === true;
		const songs = getSongLoaderState().songs;
		if (!songs.length) {
			body.append(createText("song-loader-empty", "No songs available."));
			return;
		}
		for (const song of songs) {
			const main = document.createElement("div");
			main.className = "song-loader-row-main";
			main.append(createText("song-loader-row-title", song));
			const row = List({ className: `song-loader-row${editLock && song !== loadedSong ? " is-disabled" : ""}`, content: main, isActive: song === loadedSong });
			row.tabIndex = 0;
			row.setAttribute("role", "button");
			const chooseSong = async () => {
				if (song === loadedSong || editLock) return;
				const confirmed = await ConfirmCancelPrompt({
					title: "Load song",
					message: `Load ${song}? This switches the current song in Song Analysis.`,
					confirmLabel: "Load",
					cancelLabel: "Cancel",
				});
				if (confirmed) loadSong(song);
			};
			row.onclick = () => void chooseSong();
			row.onkeydown = (event) => {
				if (event.key === "Enter" || event.key === " ") {
					event.preventDefault();
					void chooseSong();
				}
			};
			body.append(row);
		}
	};

	const unsubscribeSongs = subscribeSongLoaderState(render);
	const unsubscribeBackend = subscribeBackendStore(render);
	queueMicrotask(requestSongList);
	render();
	const card = Card(content, { variant: "outlined" });
	(card as unknown as { _cleanup?: () => void })._cleanup = () => {
		unsubscribeSongs();
		unsubscribeBackend();
	};
	return card;
}