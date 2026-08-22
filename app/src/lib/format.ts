const daNumber = new Intl.NumberFormat('da-DK', { maximumFractionDigits: 1 });
const daNumber2 = new Intl.NumberFormat('da-DK', { maximumFractionDigits: 2 });
const daNumber0 = new Intl.NumberFormat('da-DK', { maximumFractionDigits: 0 });

/** Danish number formatting tuned to the magnitude of the value. */
export function formatValue(value: number): string {
	const magnitude = Math.abs(value);
	if (magnitude >= 1000) return daNumber0.format(value);
	if (magnitude >= 10) return daNumber.format(value);
	return daNumber2.format(value);
}

export function formatSigned(value: number): string {
	return (value > 0 ? '+' : '') + formatValue(value);
}

/** Axis tick labels: compact, clean. */
export function formatTick(value: number): string {
	if (Math.abs(value) >= 1000) return daNumber0.format(value);
	return daNumber2.format(value);
}

/** "Nice" tick values covering [min, max] with roughly `count` steps. */
export function niceTicks(min: number, max: number, count = 5): number[] {
	if (min === max) {
		const pad = Math.abs(min) || 1;
		min -= pad / 10;
		max += pad / 10;
	}
	const span = max - min;
	const step = Math.pow(10, Math.floor(Math.log10(span / count)));
	const error = (span / count) / step;
	const factor = error >= 7.5 ? 10 : error >= 3.5 ? 5 : error >= 1.5 ? 2 : 1;
	const size = step * factor;
	const start = Math.ceil(min / size) * size;
	const ticks: number[] = [];
	for (let v = start; v <= max + size * 1e-9; v += size) {
		ticks.push(Math.abs(v) < size * 1e-9 ? 0 : Number(v.toPrecision(12)));
	}
	return ticks;
}
