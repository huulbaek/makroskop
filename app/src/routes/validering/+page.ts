import type { PageLoad } from './$types';

export interface OracleResult {
	id: string;
	labelDa: string;
	shock: string;
	gams: { solver: string; seconds: number; status: string };
	free: { finalResidual: number; note: string };
	responders: number | null;
	medianRel: number;
	p999Rel: number;
	maxRel: number;
	irfMedian: number | null;
	noteDa?: string;
	flagship: boolean;
	trace?: { labelDa: string; iterations: number[] };
}

export interface Validation {
	generated: string;
	model: { name: string; commit: string };
	system: {
		fullEquations: number;
		fullVariables: number;
		fullFixed: number;
		windowEquations: number;
		windowYears: string;
		maxResidualAtSolution: number;
		evalTimeSeconds: number;
	};
	machine: string;
	reproduce: string;
	recovery: { perturbation: number; iterations: number[]; medianRecovery: number };
	oracles: OracleResult[];
}

export const load: PageLoad = async ({ fetch }) => {
	const response = await fetch('/data/validation.json');
	return { validation: (await response.json()) as Validation };
};
