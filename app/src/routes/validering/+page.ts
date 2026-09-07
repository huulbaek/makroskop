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

export interface MultiplierRow {
	id: string;
	labelDa: string;
	costSeries: string;
	ours: { year1: number; year2: number; impulsePctGdp: number } | null;
	dream: { year1: number | null; year2: number | null };
	noteDa: string | null;
}

export interface Multipliers {
	generated: string;
	shockYear: number;
	definitionDa: string;
	reference: { source: string; url: string; modelDa: string };
	rows: MultiplierRow[];
}

export interface DreamComparisonRow {
	series: string;
	dream: Record<string, number | null>;
	ours: Record<string, number | null>;
}

export interface DreamComparisonShock {
	id: string;
	labelDa: string;
	scenario: string;
	scale: number;
	scaleNoteDa: string;
	noteDa: string | null;
	rows: DreamComparisonRow[];
}

export interface DreamComparison {
	generated: string;
	shockYear: number;
	columns: number[];
	reference: { source: string; url: string; modelDa: string; methodDa: string };
	series: { key: string; labelDa: string; unitDa: string }[];
	shocks: DreamComparisonShock[];
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
	const [baseline, scenario, multipliers, dreamComparison] = await Promise.all([
		loadBaseline(fetch),
		loadScenario(fetch, validation.scenario.id),
		fetch('/data/multipliers.json').then((r) => r.json() as Promise<Multipliers>),
		fetch('/data/dream_comparison.json').then((r) => r.json() as Promise<DreamComparison>)
	]);
	return { validation, years: baseline.years, scenario, multipliers, dreamComparison };
};
