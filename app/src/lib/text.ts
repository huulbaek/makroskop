/** Greedy word wrap against a width function (canvas measureText, or a heuristic). */
export function wrapLines(measure: (text: string) => number, text: string, maxWidth: number): string[] {
	const lines: string[] = [];
	let current = '';
	for (const word of text.split(' ')) {
		const candidate = current ? `${current} ${word}` : word;
		if (current && measure(candidate) > maxWidth) {
			lines.push(current);
			current = word;
		} else {
			current = candidate;
		}
	}
	if (current) lines.push(current);
	return lines;
}
