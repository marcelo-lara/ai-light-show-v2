type SongLoaderState = {
	songs: string[];
};

let state: SongLoaderState = { songs: [] };
const listeners = new Set<() => void>();

export function getSongLoaderState(): SongLoaderState {
	return state;
}

export function subscribeSongLoaderState(listener: () => void): () => void {
	listeners.add(listener);
	return () => listeners.delete(listener);
}

export function setSongLoaderSongs(songs: string[]): void {
	state = { songs: [...songs].sort((left, right) => left.localeCompare(right)) };
	for (const listener of listeners) listener();
}