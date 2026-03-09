export type PanTiltLimits = {
	maxPan: number;
	maxTilt: number;
};

export type PanTiltPoint = {
	pan: number;
	tilt: number;
};

export function pointFromPointer(
	rect: DOMRect,
	clientX: number,
	clientY: number,
	limits: PanTiltLimits,
): PanTiltPoint {
	const width = Math.max(1, rect.width);
	const height = Math.max(1, rect.height);
	const x = Math.max(0, Math.min(width, clientX - rect.left));
	const y = Math.max(0, Math.min(height, clientY - rect.top));

	return {
		pan: Math.round((x / width) * limits.maxPan),
		tilt: Math.round((y / height) * limits.maxTilt),
	};
}

export function handlePercent(point: PanTiltPoint, limits: PanTiltLimits): { left: string; top: string } {
	return {
		left: `${(point.pan / limits.maxPan) * 100}%`,
		top: `${(point.tilt / limits.maxTilt) * 100}%`,
	};
}
