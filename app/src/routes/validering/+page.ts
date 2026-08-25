import { loadBaseline, loadScenario } from '$lib/data';
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

export interface FullHorizon {
	equations: number;
	years: string;
	yearCount: number;
	perturbation: number;
	iterations: number[];
	finalResidual: number;
	medianRecovery: number;
	maxRelDev: number;
	factorSecondsUmfpack: number;
	factorSecondsPardiso: number;
	pardisoRejected: boolean;
	machine: string;
}

export interface ScenarioSolve {
	id: string;
	labelDa: string;
	shock: string;
	windowEquations: number;
	windowYears: string;
	stagesConverged: number;
	stagesRejected: number;
	freshFactorizations: number;
	factorHours: number;
	finalResidual: number;
	lastStageIterations: number[];
	lastStageLabelDa: string;
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
	solver: { newton: string; linear: string; refinement: string };
	recovery: { perturbation: number; iterations: number[]; medianRecovery: number };
	fullHorizon: FullHorizon;
	scenario: ScenarioSolve;
	oracles: OracleResult[];
}

export const load: PageLoad = async ({ fetch }) => {
	const response = await fetch('/data/validation.json');
	const validation = (await response.json()) as Validation;
	const [baseline, scenario] = await Promise.all([
		loadBaseline(fetch),
		loadScenario(fetch, validation.scenario.id)
	]);
	return { validation, years: baseline.years, scenario };
};
