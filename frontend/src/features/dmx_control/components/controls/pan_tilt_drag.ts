type DragCallbacks = {
	onMove: (clientX: number, clientY: number) => void;
	onEnd: () => void;
};

export function startMouseDrag(callbacks: DragCallbacks): () => void {
	const onMouseMove = (event: MouseEvent) => {
		callbacks.onMove(event.clientX, event.clientY);
	};
	const onMouseUp = () => {
		window.removeEventListener("mousemove", onMouseMove);
		window.removeEventListener("mouseup", onMouseUp);
		callbacks.onEnd();
	};
	window.addEventListener("mousemove", onMouseMove);
	window.addEventListener("mouseup", onMouseUp);
	return () => {
		window.removeEventListener("mousemove", onMouseMove);
		window.removeEventListener("mouseup", onMouseUp);
	};
}

export function startTouchDrag(callbacks: DragCallbacks): () => void {
	const onTouchMove = (event: TouchEvent) => {
		if (event.touches.length === 0) return;
		callbacks.onMove(event.touches[0].clientX, event.touches[0].clientY);
	};
	const onTouchEnd = () => {
		window.removeEventListener("touchmove", onTouchMove);
		window.removeEventListener("touchend", onTouchEnd);
		callbacks.onEnd();
	};
	window.addEventListener("touchmove", onTouchMove);
	window.addEventListener("touchend", onTouchEnd);
	return () => {
		window.removeEventListener("touchmove", onTouchMove);
		window.removeEventListener("touchend", onTouchEnd);
	};
}
